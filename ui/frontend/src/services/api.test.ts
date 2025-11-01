import { FridayAPIService } from './api';

// Mock fetch
global.fetch = vi.fn();
const mockFetch = global.fetch as any;

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(public url: string) {
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  send(data: string): void {
    // Mock implementation
  }

  close(): void {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

global.WebSocket = MockWebSocket as any;

describe('FridayAPIService', () => {
  let apiService: FridayAPIService;

  beforeEach(() => {
    vi.clearAllMocks();
    apiService = new FridayAPIService();
  });

  afterEach(() => {
    apiService.disconnectWebSocket();
  });

  describe('HTTP API methods', () => {
    it('submits task successfully', async () => {
      const mockResponse = { task_id: 'test-123' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const taskRequest = {
        description: 'Test task',
        context: { key: 'value' },
      };

      const result = await apiService.submitTask(taskRequest);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/tasks',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(taskRequest),
        }
      );
      expect(result).toEqual(mockResponse);
    });

    it('handles task submission errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
      });

      const taskRequest = {
        description: 'Invalid task',
        context: {},
      };

      await expect(apiService.submitTask(taskRequest)).rejects.toThrow('HTTP error! status: 400');
    });

    it('gets task status successfully', async () => {
      const mockTaskStatus = {
        id: 'test-123',
        description: 'Test task',
        status: 'completed',
        created_at: '2024-01-15T10:30:00Z',
        updated_at: '2024-01-15T10:31:00Z',
        result: 'Task completed successfully',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockTaskStatus),
      });

      const result = await apiService.getTaskStatus('test-123');

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/tasks/test-123');
      expect(result).toEqual(mockTaskStatus);
    });

    it('gets all tasks successfully', async () => {
      const mockTasks = {
        tasks: [
          { id: 'task-1', description: 'Task 1', status: 'completed' },
          { id: 'task-2', description: 'Task 2', status: 'running' },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockTasks),
      });

      const result = await apiService.getAllTasks();

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/tasks');
      expect(result).toEqual(mockTasks);
    });

    it('gets system status successfully', async () => {
      const mockStatus = {
        initialized: true,
        running: true,
        environment: 'development',
        components: {
          orchestrator: { running: true, total_tasks: 5, active_tasks: 2 },
          plugins: { loaded_plugins: 3, loaded_plugin_ids: ['plugin1', 'plugin2'] },
          memory: { sqlite_connected: true, chroma_connected: true },
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockStatus),
      });

      const result = await apiService.getSystemStatus();

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/status');
      expect(result).toEqual(mockStatus);
    });

    it('gets logs successfully', async () => {
      const mockLogs = {
        logs: [
          {
            timestamp: '2024-01-15T10:30:00Z',
            level: 'INFO',
            component: 'orchestrator',
            message: 'System started',
          },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockLogs),
      });

      const result = await apiService.getLogs({ limit: 100 });

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/logs?limit=100');
      expect(result).toEqual(mockLogs);
    });

    it('gets logs with multiple parameters', async () => {
      const mockLogs = { logs: [] };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockLogs),
      });

      await apiService.getLogs({
        limit: 50,
        level: 'ERROR',
        component: 'orchestrator'
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/logs?limit=50&level=ERROR&component=orchestrator'
      );
    });
  });

  describe('WebSocket functionality', () => {
    it('connects to WebSocket successfully', async () => {
      const connectPromise = apiService.connectWebSocket();

      // Simulate WebSocket opening
      await new Promise(resolve => setTimeout(resolve, 150));

      await expect(connectPromise).resolves.toBeUndefined();
      expect(apiService.isWebSocketConnected()).toBe(true);
    });

    it('handles WebSocket connection errors', async () => {
      // Mock WebSocket that fails to connect
      const FailingWebSocket = class extends MockWebSocket {
        constructor(url: string) {
          super(url);
          setTimeout(() => {
            if (this.onerror) {
              this.onerror(new Event('error'));
            }
          }, 50);
        }
      };

      global.WebSocket = FailingWebSocket as any;

      await expect(apiService.connectWebSocket()).rejects.toThrow('WebSocket connection failed');
    });

    it('registers and calls WebSocket message handlers', async () => {
      const messageHandler = vi.fn();

      await apiService.connectWebSocket();
      const unsubscribe = apiService.onWebSocketMessage('test_event', messageHandler);

      // Simulate receiving a message
      const mockMessage = {
        data: JSON.stringify({
          type: 'test_event',
          data: { test: 'data' },
        }),
      };

      if (apiService['ws']?.onmessage) {
        apiService['ws'].onmessage(mockMessage as MessageEvent);
      }

      expect(messageHandler).toHaveBeenCalledWith({ test: 'data' });

      // Test unsubscribe
      unsubscribe();

      if (apiService['ws']?.onmessage) {
        apiService['ws'].onmessage(mockMessage as MessageEvent);
      }

      // Handler should not be called again after unsubscribe
      expect(messageHandler).toHaveBeenCalledTimes(1);
    });

    it('ignores malformed WebSocket messages', async () => {
      const messageHandler = vi.fn();
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      await apiService.connectWebSocket();
      apiService.onWebSocketMessage('test_event', messageHandler);

      // Simulate receiving malformed JSON
      const mockMessage = {
        data: 'invalid json {',
      };

      if (apiService['ws']?.onmessage) {
        apiService['ws'].onmessage(mockMessage as MessageEvent);
      }

      expect(messageHandler).not.toHaveBeenCalled();
      expect(consoleSpy).toHaveBeenCalledWith('Failed to parse WebSocket message:', expect.any(Error));

      consoleSpy.mockRestore();
    });

    it('disconnects WebSocket properly', async () => {
      await apiService.connectWebSocket();
      expect(apiService.isWebSocketConnected()).toBe(true);

      apiService.disconnectWebSocket();

      // WebSocket should be closed
      expect(apiService.isWebSocketConnected()).toBe(false);
    });

    it('starts and stops heartbeat', async () => {
      vi.useFakeTimers();

      await apiService.connectWebSocket();
      const sendSpy = vi.spyOn(apiService['ws']!, 'send');

      apiService.startHeartbeat();

      // Fast-forward time to trigger heartbeat
      vi.advanceTimersByTime(30000);

      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify({ type: 'ping' }));

      // Stop heartbeat
      apiService.stopHeartbeat();

      // Clear the spy and advance time again
      sendSpy.mockClear();
      vi.advanceTimersByTime(30000);

      expect(sendSpy).not.toHaveBeenCalled();

      vi.useRealTimers();
    });

    it('handles WebSocket reconnection', async () => {
      const connectSpy = vi.spyOn(apiService, 'connectWebSocket');

      await apiService.connectWebSocket();

      // Simulate connection loss
      if (apiService['ws']?.onclose) {
        apiService['ws'].onclose(new CloseEvent('close'));
      }

      // Wait for reconnection attempt
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(connectSpy).toHaveBeenCalledTimes(2); // Initial + reconnect
    });

    it('limits reconnection attempts', async () => {
      const connectSpy = vi.spyOn(apiService, 'connectWebSocket');

      // Mock WebSocket that always fails
      global.WebSocket = class {
        constructor() {
          setTimeout(() => {
            if (this.onerror) {
              this.onerror(new Event('error'));
            }
          }, 10);
        }
        onopen: any = null;
        onerror: any = null;
        onclose: any = null;
        onmessage: any = null;
        readyState = 0;
        send() {}
        close() {}
      } as any;

      try {
        await apiService.connectWebSocket();
      } catch (error) {
        // Expected to fail
      }

      // Should not attempt infinite reconnections
      expect(connectSpy).toHaveBeenCalledTimes(1);
    });
  });

  describe('Error handling', () => {
    it('handles network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(apiService.submitTask({ description: 'test', context: {} }))
        .rejects.toThrow('Network error');
    });

    it('handles non-JSON responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON')),
      });

      await expect(apiService.getAllTasks()).rejects.toThrow('Invalid JSON');
    });

    it('handles 404 errors specifically', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      });

      await expect(apiService.getTaskStatus('nonexistent'))
        .rejects.toThrow('HTTP error! status: 404');
    });
  });
});
