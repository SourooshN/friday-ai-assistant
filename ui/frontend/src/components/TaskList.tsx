import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle, XCircle, AlertCircle, RefreshCw, Eye } from 'lucide-react';
import { fridayAPI } from '../services/api';
import type { TaskStatus, TaskUpdateMessage } from '../types/api';

interface TaskListProps {
  className?: string;
  autoRefresh?: boolean;
  maxTasks?: number;
}

const TaskList: React.FC<TaskListProps> = ({
  className = '',
  autoRefresh = true,
  maxTasks = 50
}) => {
  const [tasks, setTasks] = useState<TaskStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskStatus | null>(null);

  const fetchTasks = async () => {
    try {
      setError(null);
      const response = await fridayAPI.getAllTasks();
      setTasks(response.tasks.slice(0, maxTasks));
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch tasks');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [maxTasks]);

  // Listen for real-time task updates
  useEffect(() => {
    const unsubscribe = fridayAPI.onWebSocketMessage('task_update', (update: TaskUpdateMessage) => {
      setTasks(prevTasks => {
        return prevTasks.map(task => {
          if (task.id === update.task_id) {
            return { ...task, status: update.status as any, updated_at: update.timestamp };
          }
          return task;
        });
      });
    });

    return unsubscribe;
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'running':
        return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-yellow-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'failed':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'running':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  const formatDescription = (description: string, maxLength = 60) => {
    if (description.length <= maxLength) return description;
    return description.slice(0, maxLength) + '...';
  };

  const viewTaskDetails = async (taskId: string) => {
    try {
      const taskStatus = await fridayAPI.getTaskStatus(taskId);
      setSelectedTask(taskStatus);
    } catch (error) {
      console.error('Failed to fetch task details:', error);
    }
  };

  const closeModal = () => {
    setSelectedTask(null);
  };

  if (isLoading) {
    return (
      <div className={`friday-card ${className}`}>
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-600">Loading tasks...</span>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={`friday-card ${className}`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            Recent Tasks ({tasks.length})
          </h2>
          <button
            onClick={fetchTasks}
            className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            title="Refresh tasks"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md mb-4">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {tasks.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <AlertCircle className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>No tasks submitted yet</p>
            <p className="text-sm">Submit a task above to see it here</p>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <div
                key={task.id}
                className="border rounded-lg p-4 hover:shadow-sm transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-2">
                      {getStatusIcon(task.status)}
                      <span className={`px-2 py-1 text-xs rounded-full border ${getStatusColor(task.status)}`}>
                        {task.status.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500">
                        {formatTimestamp(task.created_at)}
                      </span>
                    </div>

                    <p className="text-sm text-gray-900 mb-2">
                      {formatDescription(task.description)}
                    </p>

                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span>ID: {task.id.slice(0, 8)}...</span>
                      {task.updated_at !== task.created_at && (
                        <span>Updated: {formatTimestamp(task.updated_at)}</span>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => viewTaskDetails(task.id)}
                    className="ml-4 p-2 text-gray-400 hover:text-gray-600 transition-colors"
                    title="View details"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                </div>

                {/* Show result preview for completed/failed tasks */}
                {(task.status === 'completed' || task.status === 'failed') && task.result && (
                  <div className="mt-3 pt-3 border-t">
                    <div className="bg-gray-50 rounded p-2">
                      <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-x-auto">
                        {typeof task.result === 'string'
                          ? task.result.slice(0, 200) + (task.result.length > 200 ? '...' : '')
                          : JSON.stringify(task.result, null, 2).slice(0, 200) + '...'
                        }
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Task Details Modal */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-96 overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Task Details</h3>
                <button
                  onClick={closeModal}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Task ID
                  </label>
                  <p className="text-sm text-gray-900 font-mono">{selectedTask.id}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <p className="text-sm text-gray-900">{selectedTask.description}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Status
                  </label>
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(selectedTask.status)}
                    <span className={`px-2 py-1 text-xs rounded-full border ${getStatusColor(selectedTask.status)}`}>
                      {selectedTask.status.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Created
                    </label>
                    <p className="text-sm text-gray-900">{formatTimestamp(selectedTask.created_at)}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Updated
                    </label>
                    <p className="text-sm text-gray-900">{formatTimestamp(selectedTask.updated_at)}</p>
                  </div>
                </div>

                {selectedTask.result && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Result
                    </label>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-3 rounded overflow-x-auto whitespace-pre-wrap">
                      {typeof selectedTask.result === 'string'
                        ? selectedTask.result
                        : JSON.stringify(selectedTask.result, null, 2)
                      }
                    </pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default TaskList;