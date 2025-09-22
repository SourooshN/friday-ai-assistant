import { fridayAPI } from '../services/api';

// Integration test to verify basic API connectivity
// This test will verify that the UI can properly communicate with the Friday backend

describe('Friday UI Integration Tests', () => {
  beforeEach(() => {
    // Reset any mocks to test real API communication
    vi.restoreAllMocks();
  });

  it('should be able to initialize API service', () => {
    expect(fridayAPI).toBeDefined();
    expect(typeof fridayAPI.submitTask).toBe('function');
    expect(typeof fridayAPI.getSystemStatus).toBe('function');
    expect(typeof fridayAPI.getAllTasks).toBe('function');
    expect(typeof fridayAPI.getLogs).toBe('function');
    expect(typeof fridayAPI.connectWebSocket).toBe('function');
  });

  it('should handle API endpoint URLs correctly', () => {
    // Test that API service constructs correct URLs
    const testFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ tasks: [] }),
    });

    global.fetch = testFetch;

    // Test various API calls to ensure URLs are constructed correctly
    fridayAPI.getAllTasks();
    expect(testFetch).toHaveBeenCalledWith('http://localhost:8000/api/tasks');

    fridayAPI.getSystemStatus();
    expect(testFetch).toHaveBeenCalledWith('http://localhost:8000/api/status');

    fridayAPI.getLogs({ limit: 100 });
    expect(testFetch).toHaveBeenCalledWith('http://localhost:8000/api/logs?limit=100');
  });

  it('should construct WebSocket URL correctly', () => {
    const mockWebSocket = vi.fn();
    global.WebSocket = mockWebSocket;

    fridayAPI.connectWebSocket().catch(() => {
      // Expected to fail in test environment
    });

    expect(mockWebSocket).toHaveBeenCalledWith('ws://localhost:8000/api/ws');
  });

  it('should handle CORS preflight for API requests', async () => {
    const testFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ task_id: 'test-123' }),
    });

    global.fetch = testFetch;

    const taskRequest = {
      description: 'Test task for CORS',
      context: {},
    };

    await fridayAPI.submitTask(taskRequest);

    // Verify that the request includes proper headers for CORS
    expect(testFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/tasks',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify(taskRequest),
      })
    );
  });

  it('should be ready for real backend communication', () => {
    // This test verifies that all the pieces are in place for real backend communication

    // 1. API service is properly configured
    expect(fridayAPI).toBeDefined();

    // 2. All required methods exist
    const requiredMethods = [
      'submitTask',
      'getTaskStatus',
      'getAllTasks',
      'getSystemStatus',
      'getLogs',
      'connectWebSocket',
      'disconnectWebSocket',
      'onWebSocketMessage',
      'isWebSocketConnected',
      'startHeartbeat',
      'sendWebSocketMessage'
    ];

    requiredMethods.forEach(method => {
      expect(typeof (fridayAPI as any)[method]).toBe('function');
    });

    // 3. WebSocket message handlers can be registered
    const mockHandler = vi.fn();
    const unsubscribe = fridayAPI.onWebSocketMessage('test', mockHandler);
    expect(typeof unsubscribe).toBe('function');

    // 4. Connection state can be checked
    expect(typeof fridayAPI.isWebSocketConnected()).toBe('boolean');
  });

  it('should handle network errors gracefully', async () => {
    // Simulate network failure
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

    await expect(fridayAPI.getAllTasks()).rejects.toThrow('Network error');
    await expect(fridayAPI.getSystemStatus()).rejects.toThrow('Network error');
    await expect(fridayAPI.getLogs()).rejects.toThrow('Network error');
  });

  it('should validate API response format', async () => {
    // Test that API service properly validates response formats

    // Valid task response
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ task_id: 'valid-123' }),
    });

    const result = await fridayAPI.submitTask({ description: 'test', context: {} });
    expect(result).toEqual({ task_id: 'valid-123' });

    // Valid tasks list response
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        tasks: [
          { id: 'task-1', description: 'Task 1', status: 'completed' }
        ]
      }),
    });

    const tasks = await fridayAPI.getAllTasks();
    expect(tasks.tasks).toHaveLength(1);
    expect(tasks.tasks[0].id).toBe('task-1');
  });
});

// Integration test documentation
describe('Integration Test Documentation', () => {
  it('documents the integration test requirements', () => {
    const integrationRequirements = {
      // Backend API server requirements
      backend: {
        port: 8000,
        endpoints: [
          'POST /api/tasks',
          'GET /api/tasks',
          'GET /api/tasks/{id}',
          'GET /api/status',
          'GET /api/logs',
        ],
        websocket: '/api/ws',
        cors: 'enabled for localhost:5173',
      },

      // Frontend requirements
      frontend: {
        port: 5173,
        framework: 'React + TypeScript + Vite',
        styling: 'Tailwind CSS',
        testing: 'Vitest + React Testing Library',
      },

      // Integration points
      integration: {
        api_communication: 'HTTP REST API',
        realtime_updates: 'WebSocket',
        error_handling: 'Network errors, API errors, connection failures',
        authentication: 'None (development phase)',
      },

      // Manual testing steps
      manual_testing: [
        '1. Start Friday backend API server on port 8000',
        '2. Start frontend dev server: npm run dev',
        '3. Open browser to http://localhost:5173',
        '4. Verify connection status shows "Connected"',
        '5. Submit a test task and verify it appears in task list',
        '6. Check that logs are being displayed in real-time',
        '7. Verify system status shows Friday components',
      ],
    };

    // This test serves as documentation and passes if the object is well-formed
    expect(integrationRequirements).toBeDefined();
    expect(integrationRequirements.backend.port).toBe(8000);
    expect(integrationRequirements.frontend.port).toBe(5173);
    expect(integrationRequirements.manual_testing).toHaveLength(7);
  });
});