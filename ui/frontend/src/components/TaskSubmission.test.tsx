import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TaskSubmission from './TaskSubmission';
import { fridayAPI } from '../services/api';

// Mock the API service
vi.mock('../services/api', () => ({
  fridayAPI: {
    submitTask: vi.fn(),
  },
}));

const mockFridayAPI = fridayAPI as any;

describe('TaskSubmission', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the task submission form', () => {
    render(<TaskSubmission />);

    expect(screen.getByText('Submit Task')).toBeInTheDocument();
    expect(screen.getByLabelText(/task description/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit task/i })).toBeInTheDocument();
  });

  it('validates empty task description', async () => {
    const user = userEvent.setup();
    render(<TaskSubmission />);

    const submitButton = screen.getByRole('button', { name: /submit task/i });

    await user.click(submitButton);

    expect(screen.getByText('Please enter a task description')).toBeInTheDocument();
    expect(mockFridayAPI.submitTask).not.toHaveBeenCalled();
  });

  it('submits task successfully', async () => {
    const user = userEvent.setup();
    const mockTaskId = 'test-task-123';
    const mockOnTaskSubmitted = vi.fn();

    mockFridayAPI.submitTask.mockResolvedValue({ task_id: mockTaskId });

    render(<TaskSubmission onTaskSubmitted={mockOnTaskSubmitted} />);

    const textarea = screen.getByLabelText(/task description/i);
    const submitButton = screen.getByRole('button', { name: /submit task/i });

    await user.type(textarea, 'Test task description');
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockFridayAPI.submitTask).toHaveBeenCalledWith({
        description: 'Test task description',
        context: {},
      });
    });

    expect(mockOnTaskSubmitted).toHaveBeenCalledWith(mockTaskId);
    expect(screen.getByText(`Task submitted successfully! Task ID: ${mockTaskId}`)).toBeInTheDocument();
  });

  it('handles submission errors', async () => {
    const user = userEvent.setup();
    const errorMessage = 'Network error';

    mockFridayAPI.submitTask.mockRejectedValue(new Error(errorMessage));

    render(<TaskSubmission />);

    const textarea = screen.getByLabelText(/task description/i);
    const submitButton = screen.getByRole('button', { name: /submit task/i });

    await user.type(textarea, 'Test task');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('supports Ctrl+Enter keyboard shortcut', async () => {
    const user = userEvent.setup();
    const mockTaskId = 'keyboard-task-123';

    mockFridayAPI.submitTask.mockResolvedValue({ task_id: mockTaskId });

    render(<TaskSubmission />);

    const textarea = screen.getByLabelText(/task description/i);

    await user.type(textarea, 'Keyboard shortcut test');
    await user.keyboard('{Control>}{Enter}');

    await waitFor(() => {
      expect(mockFridayAPI.submitTask).toHaveBeenCalledWith({
        description: 'Keyboard shortcut test',
        context: {},
      });
    });
  });

  it('disables submit button when submitting', async () => {
    const user = userEvent.setup();

    // Mock a slow API response
    mockFridayAPI.submitTask.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)));

    render(<TaskSubmission />);

    const textarea = screen.getByLabelText(/task description/i);
    const submitButton = screen.getByRole('button', { name: /submit task/i });

    await user.type(textarea, 'Test task');
    await user.click(submitButton);

    expect(screen.getByRole('button', { name: /submitting.../i })).toBeDisabled();
  });

  it('displays example tasks', () => {
    render(<TaskSubmission />);

    expect(screen.getByText('Example Tasks:')).toBeInTheDocument();
    expect(screen.getByText('"list files in current directory"')).toBeInTheDocument();
    expect(screen.getByText('"running applications"')).toBeInTheDocument();
  });

  it('trims whitespace from task description', async () => {
    const user = userEvent.setup();
    const mockTaskId = 'trimmed-task-123';

    mockFridayAPI.submitTask.mockResolvedValue({ task_id: mockTaskId });

    render(<TaskSubmission />);

    const textarea = screen.getByLabelText(/task description/i);
    const submitButton = screen.getByRole('button', { name: /submit task/i });

    await user.type(textarea, '   Test task with spaces   ');
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockFridayAPI.submitTask).toHaveBeenCalledWith({
        description: 'Test task with spaces',
        context: {},
      });
    });
  });
});
