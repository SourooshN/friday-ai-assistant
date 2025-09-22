import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TaskList from './TaskList';
import { fridayAPI } from '../services/api';

// Mock the API service
vi.mock('../services/api', () => ({
  fridayAPI: {
    getAllTasks: vi.fn(),
    getTaskStatus: vi.fn(),
    onWebSocketMessage: vi.fn(),
  },
}));

const mockFridayAPI = fridayAPI as any;

const mockTasks = [
  {
    id: 'task-123',
    description: 'List files in current directory',
    status: 'completed',
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T10:31:00Z',
    result: 'file1.txt\nfile2.txt\nfolder1/\n',
  },
  {
    id: 'task-456',
    description: 'Check system information',
    status: 'running',
    created_at: '2024-01-15T10:32:00Z',
    updated_at: '2024-01-15T10:32:00Z',
    result: null,
  },
  {
    id: 'task-789',
    description: 'Install new package',
    status: 'failed',
    created_at: '2024-01-15T10:28:00Z',
    updated_at: '2024-01-15T10:29:00Z',
    result: 'Error: Package not found',
  },
  {
    id: 'task-101',
    description: 'Pending task waiting for execution',
    status: 'pending',
    created_at: '2024-01-15T10:35:00Z',
    updated_at: '2024-01-15T10:35:00Z',
    result: null,
  },
];

describe('TaskList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFridayAPI.onWebSocketMessage.mockReturnValue(() => {});
  });

  it('renders loading state initially', () => {
    mockFridayAPI.getAllTasks.mockImplementation(() => new Promise(() => {}));

    render(<TaskList />);

    expect(screen.getByText('Loading tasks...')).toBeInTheDocument();
  });

  it('renders tasks successfully', async () => {
    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('Recent Tasks (4)')).toBeInTheDocument();
    });

    expect(screen.getByText('List files in current directory')).toBeInTheDocument();
    expect(screen.getByText('Check system information')).toBeInTheDocument();
  });

  it('displays task statuses with correct icons and colors', async () => {
    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    });

    expect(screen.getByText('RUNNING')).toBeInTheDocument();
    expect(screen.getByText('FAILED')).toBeInTheDocument();
    expect(screen.getByText('PENDING')).toBeInTheDocument();
  });

  it('shows result preview for completed tasks', async () => {
    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('Recent Tasks (4)')).toBeInTheDocument();
    });

    expect(screen.getByText('file1.txt\nfile2.txt\nfolder1/')).toBeInTheDocument();
  });

  it('shows result preview for failed tasks', async () => {
    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('Recent Tasks (4)')).toBeInTheDocument();
    });

    expect(screen.getByText('Error: Package not found')).toBeInTheDocument();
  });

  it('truncates long descriptions', async () => {
    const longDescriptionTask = {
      ...mockTasks[0],
      description: 'This is a very long task description that should be truncated because it exceeds the maximum length limit set for the display',
    };

    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: [longDescriptionTask] });

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText(/This is a very long task description that should be.../)).toBeInTheDocument();
    });
  });

  it('displays task IDs in truncated format', async () => {
    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('ID: task-123...')).toBeInTheDocument();
    });
  });

  it('opens task details modal when view button is clicked', async () => {
    const user = userEvent.setup();
    const taskDetail = mockTasks[0];

    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });
    mockFridayAPI.getTaskStatus.mockResolvedValue(taskDetail);

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('Recent Tasks (4)')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByTitle('View details');
    await user.click(viewButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Task Details')).toBeInTheDocument();
    });

    expect(screen.getByText('task-123')).toBeInTheDocument();
    expect(screen.getByText('List files in current directory')).toBeInTheDocument();
  });

  it('closes task details modal when close button is clicked', async () => {
    const user = userEvent.setup();
    const taskDetail = mockTasks[0];

    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });
    mockFridayAPI.getTaskStatus.mockResolvedValue(taskDetail);

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('Recent Tasks (4)')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByTitle('View details');
    await user.click(viewButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Task Details')).toBeInTheDocument();
    });

    const closeButton = screen.getByText('✕');
    await user.click(closeButton);

    expect(screen.queryByText('Task Details')).not.toBeInTheDocument();
  });

  it('supports manual refresh', async () => {
    const user = userEvent.setup();
    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('Recent Tasks (4)')).toBeInTheDocument();
    });

    const refreshButton = screen.getByTitle('Refresh tasks');
    await user.click(refreshButton);

    expect(mockFridayAPI.getAllTasks).toHaveBeenCalledTimes(2);
  });

  it('handles API errors gracefully', async () => {
    const errorMessage = 'Failed to fetch tasks';
    mockFridayAPI.getAllTasks.mockRejectedValue(new Error(errorMessage));

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('shows empty state when no tasks exist', async () => {
    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: [] });

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('No tasks submitted yet')).toBeInTheDocument();
    });

    expect(screen.getByText('Submit a task above to see it here')).toBeInTheDocument();
  });

  it('respects maxTasks limit', async () => {
    const manyTasks = Array.from({ length: 10 }, (_, i) => ({
      ...mockTasks[0],
      id: `task-${i}`,
      description: `Task ${i}`,
    }));

    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: manyTasks });

    render(<TaskList maxTasks={3} />);

    await waitFor(() => {
      expect(screen.getByText('Recent Tasks (3)')).toBeInTheDocument();
    });
  });

  it('listens for real-time task updates via WebSocket', async () => {
    let messageHandler: (update: any) => void;
    mockFridayAPI.onWebSocketMessage.mockImplementation((type: string, handler: any) => {
      if (type === 'task_update') {
        messageHandler = handler;
      }
      return () => {};
    });

    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('RUNNING')).toBeInTheDocument();
    });

    // Simulate task status update
    const taskUpdate = {
      task_id: 'task-456',
      status: 'completed',
      timestamp: '2024-01-15T10:35:00Z',
    };

    messageHandler!(taskUpdate);

    await waitFor(() => {
      expect(screen.getAllByText('COMPLETED')).toHaveLength(2);
    });
  });

  it('displays formatted timestamps', async () => {
    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('Recent Tasks (4)')).toBeInTheDocument();
    });

    // Check that timestamps are formatted (exact format depends on locale)
    const timestampElements = screen.getAllByText(/\d{1,2}\/\d{1,2}\/\d{4}|\d{1,2}:\d{2}/);
    expect(timestampElements.length).toBeGreaterThan(0);
  });

  it('shows updated timestamp when different from created timestamp', async () => {
    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText(/Updated:/)).toBeInTheDocument();
    });
  });

  it('handles task detail fetch errors', async () => {
    const user = userEvent.setup();
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });
    mockFridayAPI.getTaskStatus.mockRejectedValue(new Error('Failed to fetch task details'));

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('Recent Tasks (4)')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByTitle('View details');
    await user.click(viewButtons[0]);

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to fetch task details:', expect.any(Error));
    });

    consoleSpy.mockRestore();
  });

  it('displays JSON result properly in modal', async () => {
    const user = userEvent.setup();
    const taskWithJsonResult = {
      ...mockTasks[0],
      result: { status: 'success', data: ['item1', 'item2'] },
    };

    mockFridayAPI.getAllTasks.mockResolvedValue({ tasks: mockTasks });
    mockFridayAPI.getTaskStatus.mockResolvedValue(taskWithJsonResult);

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('Recent Tasks (4)')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByTitle('View details');
    await user.click(viewButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Task Details')).toBeInTheDocument();
    });

    expect(screen.getByText(/"status": "success"/)).toBeInTheDocument();
    expect(screen.getByText(/"data": \[/)).toBeInTheDocument();
  });
});