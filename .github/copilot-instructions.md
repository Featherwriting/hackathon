# AI Copilot Instructions - Travel Planner Hackathon

## Project Overview

**Travel Planner AI** is a React + FastAPI full-stack app combining:
- **Frontend**: React 19.2 + TypeScript with CopilotKit AI chat integration
- **Backend**: FastAPI with CopilotKit Python SDK for native action handling
- **AI Integration**: CopilotKit 1.10.6 with declarative action definitions; LLM automatically handles user requests and triggers backend actions

The core innovation: Define backend actions with parameters, and CopilotKit's LLM automatically understands user intent and calls the appropriate actions without manual keyword matching.

## Architecture Pattern

### Declarative Action Flow (CopilotKit SDK)
```
User Chat Message ("推荐一些景点")
→ CopilotKit Client sends to FastAPI /copilotkit_remote
→ CopilotKit SDK (LLM) analyzes intent
→ Automatically calls handler: fetch_featured_spots()
→ Handler returns data
→ Frontend Actions trigger UI update (if configured)
```

**Key Files:**
- `src/index.js` - Configures `runtimeUrl="http://localhost:8000/copilotkit_remote"`
- `travel-planner-backend/server.py` - FastAPI + CopilotKit SDK setup
- `travel-planner-backend/server.py` (lines 39-93) - Action definitions with parameters
- `src/hooks/useFrontendActionsSetup.ts` - Registers `window.__copilotkit_actions` for UI updates

### Backend Actions (CopilotKit Declarative)
Each action is defined with:
1. **name** - Function identifier (e.g., `fetch_featured_spots`)
2. **description** - Natural language description LLM uses to understand intent
3. **parameters** - Input parameters with types and descriptions
4. **handler** - Async function that executes the action

Example from `server.py`:
```python
action = CopilotAction(
    name="generate_itinerary",
    description="为用户生成旅游行程计划，包含每日活动安排",
    parameters=[
        {
            "name": "days",
            "type": "integer",
            "description": "行程天数，1-14天",
            "required": True
        },
        {
            "name": "city",
            "type": "string",
            "description": "目的地城市名称",
            "required": False
        }
    ],
    handler=generate_itinerary  # Async function
)
```

### Component State Pattern (unchanged)
Each content component exports:
1. **State interface** (e.g., `DayPlan`, `Spot`)
2. **Global update function** (e.g., `updateItinerary()`)
3. **Default data** (e.g., `DEFAULT_ITINERARY`)

## Critical Configuration Points

### CopilotKit Runtime URL
- **File**: `src/index.js`
- **Current**: `runtimeUrl="http://localhost:8000/copilotkit_remote"`
- **Backend endpoint**: `/copilotkit_remote` (added by `add_fastapi_endpoint()`)
- **Protocol**: CopilotKit native (not REST, not GraphQL)
- **Why**: Official SDK handles all protocol details; simpler than custom implementation

### Action Registration
- **File**: `travel-planner-backend/server.py` (lines 39-200)
- **Pattern**: Define `CopilotAction` objects and pass to `CopilotKitRemoteEndpoint`
- **Critical**: Actions must be `async` functions that return dict/data
- **LLM Integration**: Descriptions MUST be in Chinese (or match your LLM's language)

```python
actions = [
    CopilotAction(name="...", description="...", parameters=[...], handler=async_func),
    CopilotAction(name="...", description="...", parameters=[...], handler=async_func),
]
sdk = CopilotKitRemoteEndpoint(actions=actions)
add_fastapi_endpoint(app, sdk, "/copilotkit_remote")
```

### Available Backend Actions
1. **fetch_featured_spots(category)** - Returns attraction data
2. **generate_itinerary(days, city)** - Returns multi-day trip plan
3. **fetch_social_content(type)** - Returns social media posts
4. **get_transport_guide(city)** - Returns transportation options

## Development Workflow

### Installation & Setup
```bash
# Install dependencies
cd travel-planner-backend
pip install -r requirements.txt
# or manually:
pip install copilotkit fastapi uvicorn

# Install frontend deps
cd ..
npm install
```

### Starting Services
```bash
# Terminal 1: FastAPI backend (port 8000)
cd travel-planner-backend
python server.py

# Terminal 2: React frontend (port 3000)
npm start
```

### Testing Agent Integration
1. Open http://localhost:3000
2. Type in chat: "推荐几个热门景点" or "给我安排3天的行程"
3. CopilotKit SDK automatically:
   - Detects action intent from LLM response
   - Calls the appropriate handler (e.g., `fetch_featured_spots()` or `generate_itinerary()`)
   - Returns data to frontend
4. Frontend receives action result and updates UI

### Key Differences from Flask/GraphQL approach
| Flask GraphQL | FastAPI SDK |
|---|---|
| Manual keyword matching | LLM-based intent detection |
| Custom response format | Standard CopilotKit format |
| Complex JSON structure | Declarative action definitions |
| No type safety | Strong typing with Pydantic |
| Manual Frontend Actions | Automatic action invocation |

## Component-Specific Patterns

### HotActivity.tsx (unchanged)
- Still calls `/api/activity/list` REST endpoint
- No direct integration with chat actions (can be enhanced)

### JourneyHeader.tsx (unchanged)
- Still calls REST endpoints: `/api/itinerary/base-info`, `/api/itinerary/generate`
- Can be migrated to use chat actions instead

### Itinerary.tsx (unchanged)
- Receives updates from `updateItinerary()` function
- Can be triggered by `generate_itinerary` action in chat

## CSS Architecture (unchanged)
- **File**: `src/App.css`
- Layout: Flexbox for chat-section (350px) + content-section (flex: 1)
- Hover effects: Max-height reveal on activity descriptions

## Common Pitfalls & Fixes

| Issue | Solution |
|-------|----------|
| "Connection refused" on /copilotkit_remote | Ensure FastAPI is running on port 8000; check `runtimeUrl` in src/index.js |
| Actions not triggering from chat | Verify action `description` is in Chinese and clearly describes intent; check handler returns dict |
| Action parameters ignored | Ensure parameter names in definition match function signature; add `required: True/False` |
| "Module not found: copilotkit" | Run `pip install copilotkit` in venv; check requirements.txt |
| CORS errors | FastAPI includes `CORSMiddleware(allow_origins=["*"])` - should be fine |

## API Contract

### CopilotKit Endpoint
- `POST /copilotkit_remote` - Native CopilotKit protocol
  - Managed by `add_fastapi_endpoint()` - no custom parsing needed
  - Automatically calls registered action handlers based on LLM intent
  - Returns action results

### REST Endpoints (Optional, for direct component calls)
- `POST /api/itinerary/base-info`
- `POST /api/itinerary/generate`
- `POST /api/poi/list`
- `POST /api/social/feed`
- `POST /api/activity/list`

## Migration Path: From REST to Chat Actions

**Current:** Components call REST endpoints directly
```typescript
await fetch('/api/itinerary/generate', {method: 'POST', body: genPayload})
```

**Future:** Let chat handle it
```
User: "帮我安排3天的香港行程，2个人"
→ CopilotKit calls: generate_itinerary(days=3, city="香港")
→ Updates Itinerary component automatically
```

To enable: Add Frontend Actions (similar to old implementation) to return action results to UI components.

## Future Enhancement Points

1. **Add more actions** - Search flights, hotels, restaurants
2. **Streaming responses** - Enable real-time action progress
3. **Database persistence** - Replace in-memory dicts with PostgreSQL
4. **LLM provider choice** - Configure OpenAI/Claude/local models
5. **Observability** - Add logging, tracing, error handling
6. **Multi-language** - Add translations for action descriptions

## Key Dependencies & Versions
- React 19.2.0
- CopilotKit 1.10.6 (Python SDK)
- FastAPI 0.104.1
- Uvicorn 0.24.0
- Pydantic 2.5.0

## File Structure
```
travel-planner-backend/
  ├── server.py              # FastAPI + CopilotKit main file
  ├── requirements.txt       # Python dependencies
  └── app.py                 # [Can be deprecated] Old Flask GraphQL implementation
src/
  ├── index.js              # CopilotKit runtimeUrl configuration
  ├── App.tsx               # Main app, calls useFrontendActionsSetup
  └── hooks/
      └── useFrontendActionsSetup.ts  # Registers window.__copilotkit_actions
```
