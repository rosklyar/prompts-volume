# Prompts Volume - Frontend

React + TypeScript frontend for the Prompts Volume platform.

## Features

- 🔐 JWT-based authentication
- 📱 Responsive UI with Tailwind CSS
- 🎨 shadcn/ui component library
- 🚀 File-based routing (TanStack Router)
- ⚡ Optimistic updates (TanStack Query)

## Technology Stack

- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite 7
- **Routing:** TanStack Router (file-based)
- **State Management:** TanStack Query (server state)
- **Styling:** Tailwind CSS v4
- **UI Components:** shadcn/ui
- **Forms:** react-hook-form + zod

## Prerequisites

- Node.js 20+
- npm or pnpm
- Backend service running on `http://localhost:8000`

## Development Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Create a `.env` file:

```bash
VITE_API_URL=http://localhost:8000
```

### 3. Start Dev Server

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint

## Project Structure

```
frontend/
├── src/
│   ├── routes/              # Pages (file-based routing)
│   │   ├── __root.tsx       # Root layout
│   │   ├── index.tsx        # Dashboard (protected)
│   │   ├── login.tsx        # Login page
│   │   └── signup.tsx       # Signup page
│   ├── hooks/
│   │   └── useAuth.ts       # Authentication hook
│   ├── components/
│   │   ├── ui/              # shadcn/ui components
│   │   └── AuthLayout.tsx   # Auth page wrapper
│   ├── client/
│   │   └── api.ts           # Backend API client
│   ├── lib/
│   │   └── utils.ts         # Utility functions
│   ├── main.tsx             # App entry point
│   └── index.css            # Global styles
├── public/                  # Static assets
├── index.html
├── vite.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

## Routing

This app uses **TanStack Router** with file-based routing:

- `/` → Dashboard (protected, requires login)
- `/login` → Login page
- `/signup` → Signup page

### Adding New Routes

1. Create a file in `src/routes/`:
   - `about.tsx` → `/about`
   - `profile/index.tsx` → `/profile`

2. Define the route:

```tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/about')({
  component: About,
})

function About() {
  return <div>About page</div>
}
```

## Authentication

Authentication state is managed by the `useAuth` hook:

```tsx
import useAuth from '@/hooks/useAuth'

function MyComponent() {
  const { user, loginMutation, logout, isUserLoading } = useAuth()

  if (isUserLoading) return <div>Loading...</div>
  if (!user) return <div>Not logged in</div>

  return (
    <div>
      <p>Welcome, {user.email}</p>
      <button onClick={logout}>Logout</button>
    </div>
  )
}
```

### Protected Routes

Use the `beforeLoad` hook:

```tsx
import { createFileRoute, redirect } from '@tanstack/react-router'
import { isLoggedIn } from '@/hooks/useAuth'

export const Route = createFileRoute('/dashboard')({
  component: Dashboard,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: '/login' })
    }
  },
})
```

## API Integration

The backend API client is in `src/client/api.ts`:

```tsx
import { authApi } from '@/client/api'

// Login
const token = await authApi.login('user@example.com', 'password')

// Get current user
const user = await authApi.getCurrentUser(token)

// Signup
const newUser = await authApi.signup({
  email: 'user@example.com',
  password: 'password',
  full_name: 'User Name',
})
```

## UI Components

This project uses **shadcn/ui** components. To add new components:

```bash
npx shadcn@latest add [component-name]
```

Example:
```bash
npx shadcn@latest add dialog
npx shadcn@latest add dropdown-menu
```

Components are added to `src/components/ui/`.

## Styling

Uses **Tailwind CSS v4** with custom theme variables defined in `src/index.css`.

### Custom Colors

```tsx
<div className="bg-gray-900 text-white">
  <button className="bg-gray-800 hover:bg-gray-700">
    Click me
  </button>
</div>
```

## Building for Production

```bash
npm run build
```

Output will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Docker Deployment

The frontend is containerized with a multi-stage Dockerfile:

```bash
# Build and run with Docker Compose
docker-compose up -d frontend

# Or build manually
docker build -t prompts-frontend .
docker run -p 5173:5173 prompts-frontend
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API base URL | `http://localhost:8000` |

## Troubleshooting

### "Failed to fetch" errors

Ensure the backend is running and CORS is configured:
- Backend URL: `http://localhost:8000`
- CORS settings in backend `.env`: `FRONTEND_URL=http://localhost:5173`

### Route not found

Run `npm run dev` to regenerate route tree:
```bash
rm -rf src/routeTree.gen.ts
npm run dev
```

### Tailwind styles not applying

Check that `src/index.css` is imported in `src/main.tsx`:

```tsx
import './index.css'
```

## Contributing

See the main [README](../README.md) for project overview and contribution guidelines.

## Related Documentation

- [Backend README](../backend/README.md) - API documentation
- [CLAUDE.md](../CLAUDE.md) - Development guidelines
