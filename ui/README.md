# Friday AI Assistant UI

A modern React-based user interface for the Friday AI Assistant, providing task submission, real-time status monitoring, and comprehensive logging capabilities.

## Architecture

### Backend API Bridge (`/backend`)
- **FastAPI server** that bridges the Friday core system with the frontend
- **WebSocket support** for real-time updates
- **REST API endpoints** for task management, status monitoring, and logs
- **CORS enabled** for development

### Frontend UI (`/frontend`)
- **React 19 + TypeScript** for type-safe component development
- **Vite** for fast development and optimized builds
- **Tailwind CSS** for utility-first styling with custom Friday brand colors
- **Comprehensive testing** with Vitest and React Testing Library

## Features

### 🚀 Task Management
- **Task Submission**: Submit natural language tasks to Friday
- **Real-time Status**: Live updates on task progress via WebSocket
- **Task History**: View all submitted tasks with status and results
- **Task Details**: Detailed modal view for complete task information

### 📊 System Monitoring
- **Connection Status**: Visual indicators for WebSocket connectivity
- **System Status**: Real-time Friday kernel and component status
- **Component Health**: Monitor orchestrator, plugins, and memory systems
- **Plugin Management**: View loaded plugins and their status

### 📝 Logging & Debugging
- **Real-time Logs**: Live log streaming from Friday backend
- **Advanced Filtering**: Search by text, filter by level and component
- **Log Export**: Download logs as text files for analysis
- **Auto-scroll**: Automatic scrolling to latest log entries

### 🎨 User Experience
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Tab Navigation**: Organized interface with Overview, Tasks, and Logs
- **Keyboard Shortcuts**: Ctrl+Enter for quick task submission
- **Error Handling**: Graceful handling of network and API errors

## Quick Start

### Prerequisites
- Node.js 18+ (some warnings with newer packages, but functional)
- Friday AI Assistant backend running

### 1. Start the API Bridge
```bash
cd ui/backend
pip install -r requirements.txt
python api_server.py
```
The API server will start on `http://localhost:8000`

### 2. Start the Frontend
```bash
cd ui/frontend
npm install
npm run dev
```
The UI will be available at `http://localhost:5173`

### 3. Development Commands
```bash
# Frontend development
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm run test         # Run test suite
npm run lint         # Run ESLint

# Backend development
python api_server.py  # Start API server
```

## Testing

### Frontend Tests
Comprehensive test suite covering all components:

```bash
cd ui/frontend
npm test             # Run all tests
npm run test:ui      # Run with UI interface
npm run test:coverage # Run with coverage report
```

**Test Coverage:**
- ✅ **TaskSubmission**: Form validation, API integration, keyboard shortcuts
- ✅ **StatusMonitor**: Real-time status updates, error handling, auto-refresh
- ✅ **LogsView**: Filtering, search, export, real-time streaming
- ✅ **TaskList**: Task management, status updates, detailed views
- ✅ **App Integration**: Navigation, WebSocket connection, error states
- ✅ **API Service**: HTTP requests, WebSocket handling, error management

### Integration Testing
The UI includes integration tests that verify communication with the Friday backend:

```bash
# Run integration tests
npm test src/test/integration.test.ts
```

### Manual Testing Checklist
1. ✅ Start Friday backend API server on port 8000
2. ✅ Start frontend dev server: `npm run dev`
3. ✅ Open browser to `http://localhost:5173`
4. ✅ Verify connection status shows "Connected"
5. ✅ Submit a test task and verify it appears in task list
6. ✅ Check that logs are being displayed in real-time
7. ✅ Verify system status shows Friday components

## API Endpoints

The backend API bridge provides these endpoints:

### REST API
- `POST /api/tasks` - Submit new task
- `GET /api/tasks` - Get all tasks
- `GET /api/tasks/{id}` - Get specific task status
- `GET /api/status` - Get system status
- `GET /api/logs` - Get system logs (with filtering)

### WebSocket
- `ws://localhost:8000/ws` - Real-time updates
  - `task_update` - Task status changes
  - `log_entry` - New log entries
  - `status` - System status updates
  - `ping/pong` - Heartbeat messages

## Project Structure

```
ui/
├── backend/                 # FastAPI bridge server
│   ├── api_server.py       # Main API server
│   └── requirements.txt    # Python dependencies
│
└── frontend/               # React frontend
    ├── src/
    │   ├── components/     # React components
    │   │   ├── TaskSubmission.tsx
    │   │   ├── StatusMonitor.tsx
    │   │   ├── LogsView.tsx
    │   │   └── TaskList.tsx
    │   ├── services/       # API service layer
    │   │   └── api.ts
    │   ├── types/          # TypeScript definitions
    │   │   └── api.ts
    │   ├── test/           # Test utilities & integration tests
    │   └── App.tsx         # Main application
    ├── public/             # Static assets
    └── package.json        # Dependencies & scripts
```

## Configuration

### Frontend Config
- **API Base URL**: `http://localhost:8000` (configurable in `services/api.ts`)
- **WebSocket URL**: `ws://localhost:8000/ws`
- **Auto-refresh intervals**: Configurable per component
- **Tailwind CSS**: Custom Friday brand colors in `tailwind.config.js`

### Backend Config
- **Port**: 8000 (configurable in `api_server.py`)
- **CORS**: Enabled for `http://localhost:5173`
- **WebSocket heartbeat**: 30 second intervals

## Deployment

### Development
Frontend and backend run separately for hot reloading and debugging.

### Production
1. Build frontend: `npm run build`
2. Serve static files from FastAPI server
3. Configure reverse proxy (nginx) if needed
4. Update CORS settings for production domain

## Contributing

1. **Component Development**: Follow existing patterns in `/components`
2. **Type Safety**: Use TypeScript throughout, define types in `/types`
3. **Testing**: Write tests for new components and features
4. **Styling**: Use Tailwind utility classes, extend theme in `tailwind.config.js`
5. **API Changes**: Update both frontend types and backend implementation

## Phase 2.4 Completion

This UI implementation completes **Phase 2.4: UI Scaffold** with:

✅ **Modern Framework**: React + TypeScript + Vite
✅ **API Bridge**: FastAPI backend connecting to Friday core
✅ **Core Features**: Task submission, status monitoring, logs view
✅ **Real-time Updates**: WebSocket integration throughout
✅ **Comprehensive Testing**: Component and integration tests
✅ **Production Ready**: Responsive design, error handling, type safety

The UI is ready for **Phase 2.5: Testing & Integration** with the complete Friday system.