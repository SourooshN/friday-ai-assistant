import React, { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { fridayAPI } from '../services/api';
import type { TaskRequest } from '../types/api';

interface TaskSubmissionProps {
  onTaskSubmitted?: (taskId: string) => void;
  className?: string;
}

const TaskSubmission: React.FC<TaskSubmissionProps> = ({ onTaskSubmitted, className = '' }) => {
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!description.trim()) {
      setError('Please enter a task description');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const taskRequest: TaskRequest = {
        description: description.trim(),
        context: {}
      };

      const response = await fridayAPI.submitTask(taskRequest);

      setSuccess(`Task submitted successfully! Task ID: ${response.task_id}`);
      setDescription('');

      if (onTaskSubmitted) {
        onTaskSubmitted(response.task_id);
      }

    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to submit task');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSubmit(e);
    }
  };

  return (
    <div className={`friday-card ${className}`}>
      <h2 className="text-xl font-semibold text-gray-900 mb-4">
        Submit Task
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="task-description" className="block text-sm font-medium text-gray-700 mb-2">
            Task Description
          </label>
          <textarea
            id="task-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe what you want Friday to do... (Ctrl+Enter to submit)"
            rows={4}
            className="friday-textarea"
            disabled={isSubmitting}
          />
          <p className="text-xs text-gray-500 mt-1">
            Press Ctrl+Enter to submit quickly
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md fade-in">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {success && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-md fade-in">
            <p className="text-sm text-green-600">{success}</p>
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSubmitting || !description.trim()}
            className="friday-button-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span>{isSubmitting ? 'Submitting...' : 'Submit Task'}</span>
          </button>
        </div>
      </form>

      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
        <h3 className="text-sm font-medium text-blue-900 mb-2">Example Tasks:</h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• "list files in current directory"</li>
          <li>• "running applications"</li>
          <li>• "system info"</li>
          <li>• "volume status"</li>
        </ul>
      </div>
    </div>
  );
};

export default TaskSubmission;