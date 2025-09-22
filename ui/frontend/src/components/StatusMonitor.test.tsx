import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import StatusMonitor from './StatusMonitor';
import { fridayAPI } from '../services/api';

// Mock the API service
vi.mock('../services/api', () => ({
  fridayAPI: {
    getSystemStatus: vi.fn(),
    onWebSocketMessage: vi.fn(),
    isWebSocketConnected: vi.fn(),
  },
}));

const mockFridayAPI = fridayAPI as any;

const mockSystemStatus = {
  initialized: true,
  running: true,
  environment: 'development',
  components: {
    orchestrator: {
      running: true,
      total_tasks: 15,
      active_tasks: 3,
    },
    plugins: {
      loaded_plugins: 5,
      loaded_plugin_ids: ['system_control', 'file_operations', 'media_control', 'web_browser', 'calculator'],
    },
    memory: {
      sqlite_connected: true,
      chroma_connected: true,
    },
  },
};

describe('StatusMonitor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFridayAPI.isWebSocketConnected.mockReturnValue(true);
    mockFridayAPI.onWebSocketMessage.mockReturnValue(() => {});
  });

  it('renders loading state initially', () => {
    mockFridayAPI.getSystemStatus.mockImplementation(() => new Promise(() => {}));

    render(<StatusMonitor />);

    expect(screen.getByText('Loading system status...')).toBeInTheDocument();
  });

  it('renders system status successfully', async () => {
    mockFridayAPI.getSystemStatus.mockResolvedValue(mockSystemStatus);

    render(<StatusMonitor />);

    await waitFor(() => {
      expect(screen.getByText('System Status')).toBeInTheDocument();
    });

    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('DEVELOPMENT')).toBeInTheDocument();
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('displays component status correctly', async () => {
    mockFridayAPI.getSystemStatus.mockResolvedValue(mockSystemStatus);

    render(<StatusMonitor />);

    await waitFor(() => {
      expect(screen.getByText('Components')).toBeInTheDocument();
    });

    // Orchestrator component
    expect(screen.getByText('Orchestrator')).toBeInTheDocument();
    expect(screen.getByText('Total Tasks: 15')).toBeInTheDocument();
    expect(screen.getByText('Active: 3')).toBeInTheDocument();

    // Plugins component
    expect(screen.getByText('Plugins')).toBeInTheDocument();
    expect(screen.getByText('Loaded: 5')).toBeInTheDocument();

    // Memory component
    expect(screen.getByText('Memory')).toBeInTheDocument();
    expect(screen.getByText('SQLite:')).toBeInTheDocument();
    expect(screen.getByText('ChromaDB:')).toBeInTheDocument();
  });

  it('displays loaded plugins list', async () => {
    mockFridayAPI.getSystemStatus.mockResolvedValue(mockSystemStatus);

    render(<StatusMonitor />);

    await waitFor(() => {
      expect(screen.getByText('Loaded Plugins')).toBeInTheDocument();
    });

    expect(screen.getByText('system_control')).toBeInTheDocument();
    expect(screen.getByText('file_operations')).toBeInTheDocument();
    expect(screen.getByText('media_control')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    const errorMessage = 'Failed to fetch status';
    mockFridayAPI.getSystemStatus.mockRejectedValue(new Error(errorMessage));

    render(<StatusMonitor />);

    await waitFor(() => {
      expect(screen.getByText('Connection Error')).toBeInTheDocument();
    });

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('supports manual refresh', async () => {
    const user = userEvent.setup();
    mockFridayAPI.getSystemStatus.mockResolvedValue(mockSystemStatus);

    render(<StatusMonitor />);

    await waitFor(() => {
      expect(screen.getByText('System Status')).toBeInTheDocument();
    });

    const refreshButton = screen.getByTitle('Refresh status');
    await user.click(refreshButton);

    expect(mockFridayAPI.getSystemStatus).toHaveBeenCalledTimes(2);
  });

  it('shows disconnected WebSocket status', async () => {
    mockFridayAPI.getSystemStatus.mockResolvedValue(mockSystemStatus);
    mockFridayAPI.isWebSocketConnected.mockReturnValue(false);

    render(<StatusMonitor />);

    await waitFor(() => {
      expect(screen.getByText('Disconnected')).toBeInTheDocument();
    });
  });

  it('displays stopped system status', async () => {
    const stoppedStatus = {
      ...mockSystemStatus,
      running: false,
    };

    mockFridayAPI.getSystemStatus.mockResolvedValue(stoppedStatus);

    render(<StatusMonitor />);

    await waitFor(() => {
      expect(screen.getByText('Stopped')).toBeInTheDocument();
    });
  });

  it('displays initializing system status', async () => {
    const initializingStatus = {
      ...mockSystemStatus,
      initialized: false,
      running: false,
    };

    mockFridayAPI.getSystemStatus.mockResolvedValue(initializingStatus);

    render(<StatusMonitor />);

    await waitFor(() => {
      expect(screen.getByText('Initializing')).toBeInTheDocument();
    });
  });

  it('listens for real-time WebSocket updates', async () => {
    let messageHandler: (data: any) => void;
    mockFridayAPI.onWebSocketMessage.mockImplementation((type: string, handler: any) => {
      if (type === 'status') {
        messageHandler = handler;
      }
      return () => {};
    });

    mockFridayAPI.getSystemStatus.mockResolvedValue(mockSystemStatus);

    render(<StatusMonitor />);

    await waitFor(() => {
      expect(screen.getByText('Running')).toBeInTheDocument();
    });

    // Simulate WebSocket status update
    const updatedStatus = {
      ...mockSystemStatus,
      running: false,
    };

    messageHandler!(updatedStatus);

    await waitFor(() => {
      expect(screen.getByText('Stopped')).toBeInTheDocument();
    });
  });

  it('auto-refreshes when enabled', () => {
    vi.useFakeTimers();
    mockFridayAPI.getSystemStatus.mockResolvedValue(mockSystemStatus);

    render(<StatusMonitor autoRefresh={true} refreshInterval={1000} />);

    expect(mockFridayAPI.getSystemStatus).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(1000);
    expect(mockFridayAPI.getSystemStatus).toHaveBeenCalledTimes(2);

    vi.advanceTimersByTime(1000);
    expect(mockFridayAPI.getSystemStatus).toHaveBeenCalledTimes(3);

    vi.useRealTimers();
  });
});