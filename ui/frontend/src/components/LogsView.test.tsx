import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LogsView from './LogsView';
import { fridayAPI } from '../services/api';

// Mock the API service
vi.mock('../services/api', () => ({
  fridayAPI: {
    getLogs: vi.fn(),
    onWebSocketMessage: vi.fn(),
  },
}));

const mockFridayAPI = fridayAPI as any;

const mockLogs = [
  {
    timestamp: '2024-01-15T10:30:00Z',
    level: 'INFO',
    component: 'orchestrator',
    message: 'System initialized successfully',
  },
  {
    timestamp: '2024-01-15T10:31:00Z',
    level: 'DEBUG',
    component: 'plugin_manager',
    message: 'Loading plugin: system_control',
  },
  {
    timestamp: '2024-01-15T10:32:00Z',
    level: 'WARNING',
    component: 'memory',
    message: 'ChromaDB connection timeout, retrying...',
  },
  {
    timestamp: '2024-01-15T10:33:00Z',
    level: 'ERROR',
    component: 'task_executor',
    message: 'Failed to execute task: Permission denied',
  },
];

// Mock URL.createObjectURL and related methods for export functionality
Object.defineProperty(global, 'URL', {
  value: {
    createObjectURL: vi.fn(() => 'mock-url'),
    revokeObjectURL: vi.fn(),
  },
});

// Mock Blob
global.Blob = vi.fn().mockImplementation((content, options) => ({
  content,
  options,
})) as any;

describe('LogsView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFridayAPI.onWebSocketMessage.mockReturnValue(() => {});

    // Mock createElement and appendChild for download functionality
    const mockElement = {
      href: '',
      download: '',
      click: vi.fn(),
    };

    vi.spyOn(document, 'createElement').mockReturnValue(mockElement as any);
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {});
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders loading state initially', () => {
    mockFridayAPI.getLogs.mockImplementation(() => new Promise(() => {}));

    render(<LogsView />);

    expect(screen.getByText('Loading logs...')).toBeInTheDocument();
  });

  it('renders logs successfully', async () => {
    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText('System Logs (4)')).toBeInTheDocument();
    });

    expect(screen.getByText('System initialized successfully')).toBeInTheDocument();
    expect(screen.getByText('Loading plugin: system_control')).toBeInTheDocument();
  });

  it('displays log levels with correct styling', async () => {
    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText('INFO')).toBeInTheDocument();
    });

    expect(screen.getByText('DEBUG')).toBeInTheDocument();
    expect(screen.getByText('WARNING')).toBeInTheDocument();
    expect(screen.getByText('ERROR')).toBeInTheDocument();
  });

  it('filters logs by search term', async () => {
    const user = userEvent.setup();
    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText('System initialized successfully')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search logs...');
    await user.type(searchInput, 'plugin');

    expect(screen.getByText('Loading plugin: system_control')).toBeInTheDocument();
    expect(screen.queryByText('System initialized successfully')).not.toBeInTheDocument();
  });

  it('filters logs by level', async () => {
    const user = userEvent.setup();
    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText('System Logs (4)')).toBeInTheDocument();
    });

    const levelSelect = screen.getByDisplayValue('All Levels');
    await user.selectOptions(levelSelect, 'ERROR');

    expect(screen.getByText('Failed to execute task: Permission denied')).toBeInTheDocument();
    expect(screen.queryByText('System initialized successfully')).not.toBeInTheDocument();
  });

  it('filters logs by component', async () => {
    const user = userEvent.setup();
    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText('System Logs (4)')).toBeInTheDocument();
    });

    const componentSelect = screen.getByDisplayValue('All Components');
    await user.selectOptions(componentSelect, 'orchestrator');

    expect(screen.getByText('System initialized successfully')).toBeInTheDocument();
    expect(screen.queryByText('Loading plugin: system_control')).not.toBeInTheDocument();
  });

  it('supports manual refresh', async () => {
    const user = userEvent.setup();
    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText('System Logs (4)')).toBeInTheDocument();
    });

    const refreshButton = screen.getByTitle('Refresh logs');
    await user.click(refreshButton);

    expect(mockFridayAPI.getLogs).toHaveBeenCalledTimes(2);
  });

  it('exports logs as text file', async () => {
    const user = userEvent.setup();
    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText('System Logs (4)')).toBeInTheDocument();
    });

    const exportButton = screen.getByTitle('Export logs');
    await user.click(exportButton);

    expect(global.Blob).toHaveBeenCalledWith(
      [expect.stringContaining('[2024-01-15T10:30:00Z] INFO (orchestrator): System initialized successfully')],
      { type: 'text/plain' }
    );
    expect(global.URL.createObjectURL).toHaveBeenCalled();
  });

  it('clears logs', async () => {
    const user = userEvent.setup();
    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText('System Logs (4)')).toBeInTheDocument();
    });

    const clearButton = screen.getByTitle('Clear logs');
    await user.click(clearButton);

    expect(screen.getByText('System Logs (0)')).toBeInTheDocument();
    expect(screen.getByText('No logs available')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    const errorMessage = 'Failed to fetch logs';
    mockFridayAPI.getLogs.mockRejectedValue(new Error(errorMessage));

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('listens for real-time log updates', async () => {
    let messageHandler: (log: any) => void;
    mockFridayAPI.onWebSocketMessage.mockImplementation((type: string, handler: any) => {
      if (type === 'log_entry') {
        messageHandler = handler;
      }
      return () => {};
    });

    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText('System Logs (4)')).toBeInTheDocument();
    });

    // Simulate new log entry via WebSocket
    const newLog = {
      timestamp: '2024-01-15T10:34:00Z',
      level: 'INFO',
      component: 'api_server',
      message: 'New WebSocket connection established',
    };

    messageHandler!(newLog);

    await waitFor(() => {
      expect(screen.getByText('System Logs (5)')).toBeInTheDocument();
    });

    expect(screen.getByText('New WebSocket connection established')).toBeInTheDocument();
  });

  it('toggles auto-scroll functionality', async () => {
    const user = userEvent.setup();
    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText('System Logs (4)')).toBeInTheDocument();
    });

    const autoScrollCheckbox = screen.getByLabelText('Auto-scroll');
    expect(autoScrollCheckbox).toBeChecked();

    await user.click(autoScrollCheckbox);
    expect(autoScrollCheckbox).not.toBeChecked();
  });

  it('shows empty state when no logs match filters', async () => {
    const user = userEvent.setup();
    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView />);

    await waitFor(() => {
      expect(screen.getByText('System Logs (4)')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search logs...');
    await user.type(searchInput, 'nonexistent');

    expect(screen.getByText('No logs match the current filters')).toBeInTheDocument();
  });

  it('respects maxLogs limit', async () => {
    mockFridayAPI.getLogs.mockResolvedValue({ logs: mockLogs });

    render(<LogsView maxLogs={2} />);

    await waitFor(() => {
      expect(mockFridayAPI.getLogs).toHaveBeenCalledWith({ limit: 2 });
    });
  });
});