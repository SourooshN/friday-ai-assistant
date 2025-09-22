// Friday API Service

import {
  TaskRequest,
  TaskResponse,
  TaskStatus,
  SystemStatus,
  LogsResponse,
  TasksResponse,
  WebSocketMessage,
} from '../types/api';

const API_BASE_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/api/ws';

class FridayAPIService {
  private wsConnection: WebSocket | null = null;
  private wsListeners: Map<string, ((data: any) => void)[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000;

  // HTTP API Methods

  async getSystemStatus(): Promise<SystemStatus> {
    const response = await fetch(`${API_BASE_URL}/api/status`);
    if (!response.ok) {
      throw new Error(`Failed to get system status: ${response.statusText}`);
    }
    return response.json();
  }

  async submitTask(task: TaskRequest): Promise<TaskResponse> {
    const response = await fetch(`${API_BASE_URL}/api/tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(task),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'Failed to submit task');
    }

    return response.json();
  }

  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`);
    if (!response.ok) {
      throw new Error(`Failed to get task status: ${response.statusText}`);
    }
    return response.json();
  }

  async getAllTasks(): Promise<TasksResponse> {
    const response = await fetch(`${API_BASE_URL}/api/tasks`);
    if (!response.ok) {
      throw new Error(`Failed to get tasks: ${response.statusText}`);
    }
    return response.json();
  }

  async getLogs(params?: {
    limit?: number;
    level?: string;
    component?: string;
  }): Promise<LogsResponse> {
    const url = new URL(`${API_BASE_URL}/api/logs`);

    if (params?.limit) url.searchParams.set('limit', params.limit.toString());
    if (params?.level) url.searchParams.set('level', params.level);
    if (params?.component) url.searchParams.set('component', params.component);

    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`Failed to get logs: ${response.statusText}`);
    }
    return response.json();
  }

  // WebSocket Methods

  connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.wsConnection = new WebSocket(WS_URL);

        this.wsConnection.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          resolve();
        };

        this.wsConnection.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.wsConnection.onclose = (event) => {
          console.log('WebSocket disconnected:', event.reason);
          this.wsConnection = null;
          this.attemptReconnect();
        };

        this.wsConnection.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  private handleWebSocketMessage(message: WebSocketMessage) {
    const listeners = this.wsListeners.get(message.type) || [];
    listeners.forEach(listener => {
      try {
        listener(message.data);
      } catch (error) {
        console.error('Error in WebSocket listener:', error);
      }
    });
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      this.connectWebSocket().catch(error => {
        console.error('Reconnect failed:', error);
      });
    }, delay);
  }

  onWebSocketMessage(type: string, callback: (data: any) => void) {
    if (!this.wsListeners.has(type)) {
      this.wsListeners.set(type, []);
    }
    this.wsListeners.get(type)!.push(callback);

    // Return unsubscribe function
    return () => {
      const listeners = this.wsListeners.get(type);
      if (listeners) {
        const index = listeners.indexOf(callback);
        if (index > -1) {
          listeners.splice(index, 1);
        }
      }
    };
  }

  sendWebSocketMessage(message: any) {
    if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
      this.wsConnection.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected');
    }
  }

  disconnectWebSocket() {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = null;
    }
  }

  // Utility method to start periodic ping
  startHeartbeat(interval = 30000) {
    const pingInterval = setInterval(() => {
      if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
        this.sendWebSocketMessage({ type: 'ping' });
      } else {
        clearInterval(pingInterval);
      }
    }, interval);

    return () => clearInterval(pingInterval);
  }

  isWebSocketConnected(): boolean {
    return this.wsConnection?.readyState === WebSocket.OPEN;
  }
}

// Export singleton instance
export const fridayAPI = new FridayAPIService();
export default fridayAPI;