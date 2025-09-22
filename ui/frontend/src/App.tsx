import React, { useEffect, useState } from 'react';
import { Bot, Wifi, WifiOff } from 'lucide-react';
import TaskSubmission from './components/TaskSubmission';
import StatusMonitor from './components/StatusMonitor';
import LogsView from './components/LogsView';
import TaskList from './components/TaskList';
import { fridayAPI } from './services/api';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'tasks' | 'logs'>('overview');

  useEffect(() => {
    // Initialize WebSocket connection
    const initConnection = async () => {
      try {
        await fridayAPI.connectWebSocket();
        setIsConnected(true);
        setConnectionError(null);

        // Start heartbeat
        fridayAPI.startHeartbeat();

      } catch (error) {
        setConnectionError(error instanceof Error ? error.message : 'Connection failed');
        setIsConnected(false);
      }
    };

    initConnection();

    // Cleanup on unmount
    return () => {
      fridayAPI.disconnectWebSocket();
    };
  }, []);

  const handleTaskSubmitted = (taskId: string) => {
    // Switch to tasks tab when a task is submitted
    setActiveTab('tasks');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Bot className="w-8 h-8 text-friday-600" />
                <h1 className="text-2xl font-bold text-gray-900">Friday AI Assistant</h1>
              </div>
              <div className="flex items-center space-x-2">
                {isConnected ? (
                  <>
                    <Wifi className="w-4 h-4 text-green-500" />
                    <span className="text-sm text-green-600">Connected</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-4 h-4 text-red-500" />
                    <span className="text-sm text-red-600">
                      {connectionError ? 'Connection Error' : 'Disconnected'}
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Navigation Tabs */}
            <nav className="flex space-x-4">
              {[
                { id: 'overview', label: 'Overview' },
                { id: 'tasks', label: 'Tasks' },
                { id: 'logs', label: 'Logs' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'bg-friday-100 text-friday-700'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Connection Error Banner */}
        {connectionError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
            <div className="flex items-center">
              <WifiOff className="w-5 h-5 text-red-500 mr-2" />
              <div>
                <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
                <p className="text-sm text-red-700 mt-1">{connectionError}</p>
                <p className="text-xs text-red-600 mt-1">
                  Make sure the Friday API server is running on localhost:8000
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Top Row - Task Submission and Status */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <TaskSubmission onTaskSubmitted={handleTaskSubmitted} />
              <StatusMonitor />
            </div>

            {/* Bottom Row - Recent Tasks */}
            <TaskList maxTasks={5} />
          </div>
        )}

        {activeTab === 'tasks' && (
          <div className="space-y-8">
            <TaskSubmission onTaskSubmitted={handleTaskSubmitted} />
            <TaskList />
          </div>
        )}

        {activeTab === 'logs' && (
          <LogsView className="h-96" />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Friday AI Assistant UI - Connected to backend via WebSocket
            </p>
            <div className="flex items-center space-x-4 text-xs text-gray-400">
              <span>API: localhost:8000</span>
              <span>WebSocket: {isConnected ? 'Connected' : 'Disconnected'}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App
