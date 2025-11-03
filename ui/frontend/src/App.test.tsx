import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import { fridayAPI } from './services/api';

// Mock the API service
vi.mock('./services/api', () => ({
  fridayAPI: {
    connectWebSocket: vi.fn(),
    disconnectWebSocket: vi.fn(),
    startHeartbeat: vi.fn(),
  },
}));

// Mock all components to focus on App-level integration
vi.mock('./components/TaskSubmission', () => ({
  default: ({ onTaskSubmitted }: { onTaskSubmitted?: (taskId: string) => void }) => (
    <div data-testid="task-submission">
      <button onClick={() => onTaskSubmitted?.('test-task-123')}>Submit Task</button>
    </div>
  ),
}));

vi.mock('./components/StatusMonitor', () => ({
  default: () => <div data-testid="status-monitor">Status Monitor</div>,
}));

vi.mock('./components/LogsView', () => ({
  default: ({ className }: { className?: string }) => (
    <div data-testid="logs-view" className={className}>Logs View</div>
  ),
}));

vi.mock('./components/TaskList', () => ({
  default: ({ maxTasks }: { maxTasks?: number }) => (
    <div data-testid="task-list">Task List {maxTasks ? `(max: ${maxTasks})` : ''}</div>
  ),
}));

const mockFridayAPI = fridayAPI as any;

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the main application layout', async () => {
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    expect(screen.getByText('Friday AI Assistant')).toBeInTheDocument();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Tasks')).toBeInTheDocument();
    expect(screen.getByText('Logs')).toBeInTheDocument();
  });

  it('initializes WebSocket connection on mount', async () => {
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    await waitFor(() => {
      expect(mockFridayAPI.connectWebSocket).toHaveBeenCalledTimes(1);
    });

    expect(mockFridayAPI.startHeartbeat).toHaveBeenCalledTimes(1);
  });

  it('shows connected status when WebSocket connects successfully', async () => {
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    expect(screen.queryByText('Connection Error')).not.toBeInTheDocument();
  });

  it('shows connection error when WebSocket fails to connect', async () => {
    const errorMessage = 'Failed to connect to WebSocket';
    mockFridayAPI.connectWebSocket.mockRejectedValue(new Error(errorMessage));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Connection Error')).toBeInTheDocument();
    });

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.getByText('Make sure the Friday API server is running on localhost:8000')).toBeInTheDocument();
  });

  it('switches between navigation tabs', async () => {
    const user = userEvent.setup();
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    // Initially on Overview tab
    expect(screen.getByTestId('task-submission')).toBeInTheDocument();
    expect(screen.getByTestId('status-monitor')).toBeInTheDocument();
    expect(screen.getByTestId('task-list')).toBeInTheDocument();

    // Switch to Tasks tab
    await user.click(screen.getByText('Tasks'));

    expect(screen.getAllByTestId('task-submission')).toHaveLength(1);
    expect(screen.getAllByTestId('task-list')).toHaveLength(1);
    expect(screen.queryByTestId('status-monitor')).not.toBeInTheDocument();

    // Switch to Logs tab
    await user.click(screen.getByText('Logs'));

    expect(screen.getByTestId('logs-view')).toBeInTheDocument();
    expect(screen.queryByTestId('task-submission')).not.toBeInTheDocument();
    expect(screen.queryByTestId('status-monitor')).not.toBeInTheDocument();
  });

  it('shows limited tasks on overview tab', async () => {
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Task List (max: 5)')).toBeInTheDocument();
    });
  });

  it('shows full task list on tasks tab', async () => {
    const user = userEvent.setup();
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    await user.click(screen.getByText('Tasks'));

    expect(screen.getByText('Task List')).toBeInTheDocument();
    expect(screen.queryByText('Task List (max: 5)')).not.toBeInTheDocument();
  });

  it('switches to tasks tab when task is submitted', async () => {
    const user = userEvent.setup();
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    // Initially on Overview tab
    expect(screen.getByText('Overview')).toHaveClass('bg-friday-100');

    // Submit a task (this triggers the onTaskSubmitted callback)
    await user.click(screen.getByText('Submit Task'));

    // Should switch to Tasks tab
    await waitFor(() => {
      expect(screen.getByText('Tasks')).toHaveClass('bg-friday-100');
    });
  });

  it('applies correct styling to active tab', async () => {
    const user = userEvent.setup();
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    // Overview tab should be active initially
    expect(screen.getByText('Overview')).toHaveClass('bg-friday-100', 'text-friday-700');
    expect(screen.getByText('Tasks')).toHaveClass('text-gray-500');

    // Click Tasks tab
    await user.click(screen.getByText('Tasks'));

    expect(screen.getByText('Tasks')).toHaveClass('bg-friday-100', 'text-friday-700');
    expect(screen.getByText('Overview')).toHaveClass('text-gray-500');
  });

  it('displays footer with connection information', async () => {
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    expect(screen.getByText('Friday AI Assistant UI - Connected to backend via WebSocket')).toBeInTheDocument();
    expect(screen.getByText('API: localhost:8000')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('WebSocket: Connected')).toBeInTheDocument();
    });
  });

  it('shows disconnected status in footer when connection fails', async () => {
    mockFridayAPI.connectWebSocket.mockRejectedValue(new Error('Connection failed'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('WebSocket: Disconnected')).toBeInTheDocument();
    });
  });

  it('disconnects WebSocket on unmount', () => {
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    const { unmount } = render(<App />);

    unmount();

    expect(mockFridayAPI.disconnectWebSocket).toHaveBeenCalledTimes(1);
  });

  it('shows connection error banner with retry information', async () => {
    const errorMessage = 'WebSocket connection timeout';
    mockFridayAPI.connectWebSocket.mockRejectedValue(new Error(errorMessage));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Connection Error')).toBeInTheDocument();
    });

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.getByText('Make sure the Friday API server is running on localhost:8000')).toBeInTheDocument();
  });

  it('displays correct connection status icon', async () => {
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    // The Wifi icon should be present for connected state
    const connectionStatus = screen.getByText('Connected').parentElement;
    expect(connectionStatus).toBeInTheDocument();
  });

  it('displays disconnected status icon when connection fails', async () => {
    mockFridayAPI.connectWebSocket.mockRejectedValue(new Error('Connection failed'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Connection Error')).toBeInTheDocument();
    });

    // The WifiOff icon should be present for disconnected state
    const connectionStatus = screen.getByText('Connection Error').parentElement;
    expect(connectionStatus).toBeInTheDocument();
  });

  it('handles tab navigation keyboard accessibility', async () => {
    const user = userEvent.setup();
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    const overviewTab = screen.getByText('Overview');
    const tasksTab = screen.getByText('Tasks');
    const logsTab = screen.getByText('Logs');

    // Focus and navigate using keyboard
    overviewTab.focus();
    await user.keyboard('{Tab}');
    expect(tasksTab).toHaveFocus();

    await user.keyboard('{Tab}');
    expect(logsTab).toHaveFocus();

    // Activate with Enter or Space
    await user.keyboard('{Enter}');
    expect(logsTab).toHaveClass('bg-friday-100', 'text-friday-700');
  });

  it('maintains responsive layout classes', async () => {
    mockFridayAPI.connectWebSocket.mockResolvedValue(undefined);

    render(<App />);

    const mainContent = screen.getByRole('main');
    expect(mainContent).toHaveClass('max-w-7xl', 'mx-auto', 'px-4', 'sm:px-6', 'lg:px-8', 'py-8');

    // Check grid layout on overview
    const overviewGrid = screen.getByTestId('task-submission').parentElement?.parentElement;
    expect(overviewGrid).toHaveClass('grid', 'grid-cols-1', 'lg:grid-cols-2', 'gap-8');
  });
});
