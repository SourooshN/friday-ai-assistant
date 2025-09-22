import React, { useState, useEffect } from 'react';
import { RefreshCw, Server, Database, Cpu, Plug } from 'lucide-react';
import { fridayAPI } from '../services/api';
import type { SystemStatus } from '../types/api';

interface StatusMonitorProps {
  autoRefresh?: boolean;
  refreshInterval?: number;
  className?: string;
}

const StatusMonitor: React.FC<StatusMonitorProps> = ({
  autoRefresh = true,
  refreshInterval = 5000,
  className = ''
}) => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchStatus = async () => {
    try {
      setError(null);
      const systemStatus = await fridayAPI.getSystemStatus();
      setStatus(systemStatus);
      setLastUpdated(new Date());
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch status');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();

    if (autoRefresh) {
      const interval = setInterval(fetchStatus, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  // Listen for WebSocket status updates
  useEffect(() => {
    const unsubscribe = fridayAPI.onWebSocketMessage('status', (data: SystemStatus) => {
      setStatus(data);
      setLastUpdated(new Date());
    });

    return unsubscribe;
  }, []);

  const getStatusColor = (running: boolean, initialized: boolean) => {
    if (!initialized) return 'text-gray-500';
    return running ? 'text-green-500' : 'text-red-500';
  };

  const getStatusDot = (running: boolean, initialized: boolean) => {
    if (!initialized) return 'status-pending';
    return running ? 'status-running' : 'status-stopped';
  };

  if (isLoading) {
    return (
      <div className={`friday-card ${className}`}>
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-600">Loading system status...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`friday-card ${className}`}>
        <div className="text-center py-8">
          <Server className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Connection Error</h3>
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={fetchStatus}
            className="friday-button-primary flex items-center mx-auto"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`friday-card ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          <Server className="w-5 h-5 mr-2" />
          System Status
        </h2>
        <button
          onClick={fetchStatus}
          className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
          title="Refresh status"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {status && (
        <div className="space-y-6">
          {/* Main Status */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="flex items-center justify-center mb-2">
                <span className={getStatusDot(status.running, status.initialized)}></span>
                <span className={`font-medium ${getStatusColor(status.running, status.initialized)}`}>
                  {status.initialized ? (status.running ? 'Running' : 'Stopped') : 'Initializing'}
                </span>
              </div>
              <p className="text-sm text-gray-600">System Status</p>
            </div>

            <div className="text-center">
              <div className="text-lg font-medium text-gray-900 mb-1">
                {status.environment.toUpperCase()}
              </div>
              <p className="text-sm text-gray-600">Environment</p>
            </div>

            <div className="text-center">
              <div className="text-lg font-medium text-gray-900 mb-1">
                {fridayAPI.isWebSocketConnected() ? (
                  <span className="text-green-600">Connected</span>
                ) : (
                  <span className="text-red-600">Disconnected</span>
                )}
              </div>
              <p className="text-sm text-gray-600">WebSocket</p>
            </div>
          </div>

          {/* Components Status */}
          <div className="border-t pt-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Components</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

              {/* Orchestrator */}
              {status.components.orchestrator && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center mb-2">
                    <Cpu className="w-4 h-4 mr-2 text-blue-500" />
                    <span className="font-medium">Orchestrator</span>
                    <span className={status.components.orchestrator.running ? 'status-running' : 'status-stopped'}></span>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <div>Total Tasks: {status.components.orchestrator.total_tasks}</div>
                    <div>Active: {status.components.orchestrator.active_tasks}</div>
                  </div>
                </div>
              )}

              {/* Plugins */}
              {status.components.plugins && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center mb-2">
                    <Plug className="w-4 h-4 mr-2 text-green-500" />
                    <span className="font-medium">Plugins</span>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <div>Loaded: {status.components.plugins.loaded_plugins}</div>
                    <div className="truncate" title={status.components.plugins.loaded_plugin_ids.join(', ')}>
                      {status.components.plugins.loaded_plugin_ids.slice(0, 2).join(', ')}
                      {status.components.plugins.loaded_plugin_ids.length > 2 && '...'}
                    </div>
                  </div>
                </div>
              )}

              {/* Memory */}
              {status.components.memory && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center mb-2">
                    <Database className="w-4 h-4 mr-2 text-purple-500" />
                    <span className="font-medium">Memory</span>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <div className="flex items-center">
                      SQLite:
                      <span className={status.components.memory.sqlite_connected ? 'status-running ml-1' : 'status-stopped ml-1'}></span>
                    </div>
                    <div className="flex items-center">
                      ChromaDB:
                      <span className={status.components.memory.chroma_connected ? 'status-running ml-1' : 'status-stopped ml-1'}></span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Plugin Details */}
          {status.components.plugins && status.components.plugins.loaded_plugin_ids.length > 0 && (
            <div className="border-t pt-6">
              <h3 className="text-lg font-medium text-gray-900 mb-3">Loaded Plugins</h3>
              <div className="flex flex-wrap gap-2">
                {status.components.plugins.loaded_plugin_ids.map((plugin) => (
                  <span
                    key={plugin}
                    className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                  >
                    {plugin}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Last Updated */}
          {lastUpdated && (
            <div className="text-xs text-gray-500 text-center border-t pt-4">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default StatusMonitor;