import React, { useState, useEffect, useRef } from 'react';
import { Search, Filter, Download, Trash2, RefreshCw } from 'lucide-react';
import { fridayAPI } from '../services/api';
import type { LogEntry } from '../types/api';

interface LogsViewProps {
  autoRefresh?: boolean;
  maxLogs?: number;
  className?: string;
}

const LogsView: React.FC<LogsViewProps> = ({
  autoRefresh = true,
  maxLogs = 1000,
  className = ''
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<string>('');
  const [selectedComponent, setSelectedComponent] = useState<string>('');
  const [autoScroll, setAutoScroll] = useState(true);

  const logsContainerRef = useRef<HTMLDivElement>(null);

  const logLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];

  const fetchLogs = async () => {
    try {
      setError(null);
      const response = await fridayAPI.getLogs({ limit: maxLogs });
      setLogs(response.logs);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch logs');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [maxLogs]);

  // Listen for real-time log updates via WebSocket
  useEffect(() => {
    const unsubscribe = fridayAPI.onWebSocketMessage('log_entry', (logEntry: LogEntry) => {
      setLogs(prevLogs => {
        const newLogs = [...prevLogs, logEntry];
        // Keep only the most recent logs
        return newLogs.slice(-maxLogs);
      });
    });

    return unsubscribe;
  }, [maxLogs]);

  // Filter logs when search term or filters change
  useEffect(() => {
    let filtered = logs;

    if (searchTerm) {
      filtered = filtered.filter(log =>
        log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.component.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (selectedLevel) {
      filtered = filtered.filter(log => log.level === selectedLevel);
    }

    if (selectedComponent) {
      filtered = filtered.filter(log => log.component === selectedComponent);
    }

    setFilteredLogs(filtered);
  }, [logs, searchTerm, selectedLevel, selectedComponent]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll]);

  const getLogLevelClass = (level: string) => {
    switch (level.toLowerCase()) {
      case 'debug': return 'log-debug';
      case 'info': return 'log-info';
      case 'warning': return 'log-warning';
      case 'error': return 'log-error';
      default: return 'text-gray-600';
    }
  };

  const getLogLevelBadgeClass = (level: string) => {
    switch (level.toLowerCase()) {
      case 'debug': return 'bg-gray-100 text-gray-700';
      case 'info': return 'bg-blue-100 text-blue-700';
      case 'warning': return 'bg-yellow-100 text-yellow-700';
      case 'error': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const clearLogs = () => {
    setLogs([]);
    setFilteredLogs([]);
  };

  const exportLogs = () => {
    const logText = filteredLogs.map(log =>
      `[${log.timestamp}] ${log.level} (${log.component}): ${log.message}`
    ).join('\n');

    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `friday-logs-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString();
    } catch {
      return timestamp;
    }
  };

  // Get unique components for filter dropdown
  const uniqueComponents = Array.from(new Set(logs.map(log => log.component))).sort();

  return (
    <div className={`friday-card ${className}`}>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            System Logs ({filteredLogs.length})
          </h2>
          <div className="flex items-center space-x-2">
            <button
              onClick={fetchLogs}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Refresh logs"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={exportLogs}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Export logs"
            >
              <Download className="w-4 h-4" />
            </button>
            <button
              onClick={clearLogs}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Clear logs"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-4 p-4 bg-gray-50 rounded-lg">
          {/* Search */}
          <div className="flex-1 min-w-64">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="friday-input pl-10"
              />
            </div>
          </div>

          {/* Level Filter */}
          <div className="min-w-32">
            <select
              value={selectedLevel}
              onChange={(e) => setSelectedLevel(e.target.value)}
              className="friday-input"
            >
              <option value="">All Levels</option>
              {logLevels.map(level => (
                <option key={level} value={level}>{level}</option>
              ))}
            </select>
          </div>

          {/* Component Filter */}
          <div className="min-w-40">
            <select
              value={selectedComponent}
              onChange={(e) => setSelectedComponent(e.target.value)}
              className="friday-input"
            >
              <option value="">All Components</option>
              {uniqueComponents.map(component => (
                <option key={component} value={component}>{component}</option>
              ))}
            </select>
          </div>

          {/* Auto-scroll toggle */}
          <div className="flex items-center">
            <label className="flex items-center space-x-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-gray-300 text-friday-600 focus:ring-friday-500"
              />
              <span>Auto-scroll</span>
            </label>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md mb-4">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
            <span className="ml-2 text-gray-600">Loading logs...</span>
          </div>
        )}

        {/* Logs Container */}
        {!isLoading && (
          <div
            ref={logsContainerRef}
            className="flex-1 overflow-y-auto bg-gray-900 rounded-lg p-4 text-sm font-mono"
            style={{ maxHeight: '500px' }}
          >
            {filteredLogs.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                {logs.length === 0 ? 'No logs available' : 'No logs match the current filters'}
              </div>
            ) : (
              <div className="space-y-1">
                {filteredLogs.map((log, index) => (
                  <div
                    key={`${log.timestamp}-${index}`}
                    className="flex items-start space-x-3 py-1 hover:bg-gray-800 rounded px-2 fade-in"
                  >
                    <span className="text-gray-400 text-xs min-w-20">
                      {formatTimestamp(log.timestamp)}
                    </span>
                    <span className={`px-2 py-0.5 text-xs rounded uppercase font-bold min-w-16 text-center ${getLogLevelBadgeClass(log.level)}`}>
                      {log.level}
                    </span>
                    <span className="text-gray-300 text-xs min-w-24 truncate">
                      {log.component}
                    </span>
                    <span className={`flex-1 ${getLogLevelClass(log.level)}`}>
                      {log.message}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        {!isLoading && (
          <div className="text-xs text-gray-500 text-center mt-4 pt-2 border-t">
            Showing {filteredLogs.length} of {logs.length} logs
            {autoRefresh && ' • Auto-refreshing via WebSocket'}
          </div>
        )}
      </div>
    </div>
  );
};

export default LogsView;