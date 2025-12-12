# Frontend Development Guide

This file provides guidance for working with the React + TypeScript frontend.

## Tech Stack

- React 18 + TypeScript
- Vite 7 (build tool)
- TanStack Router (file-based routing)
- TanStack Query (server state)
- Tailwind CSS v4
- shadcn/ui components
- react-hook-form + zod (forms)

## Development Commands

- `npm install` - Install dependencies
- `npm run dev` - Start dev server (http://localhost:5173)
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Project Structure

```
frontend/src/
├── routes/              # Pages (file-based routing)
│   ├── __root.tsx       # Root layout with QueryClientProvider
│   ├── index.tsx        # Dashboard (protected)
│   ├── login.tsx        # Login page
│   └── signup.tsx       # Signup page
├── hooks/
│   └── useAuth.ts       # Authentication hook
├── components/
│   ├── ui/              # shadcn/ui components
│   └── AuthLayout.tsx   # Auth page wrapper
├── client/
│   └── api.ts           # Backend API client
├── lib/
│   └── utils.ts         # Utility functions (cn helper)
├── main.tsx             # App entry point
└── index.css            # Global styles + Tailwind
```

## Routing Patterns

Uses **TanStack Router** with file-based routing:

### Creating a Route

**File:** `src/routes/about.tsx`
```tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/about')({
  component: About,
})

function About() {
  return <div>About page</div>
}
```

### Protected Routes

Use `beforeLoad` to check authentication:
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

### Redirecting Authenticated Users

Redirect logged-in users away from auth pages:
```tsx
export const Route = createFileRoute('/login')({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({ to: '/' })
    }
  },
})
```

## Authentication

### Using the useAuth Hook

```tsx
import useAuth from '@/hooks/useAuth'

function MyComponent() {
  const { user, loginMutation, signUpMutation, logout, isUserLoading } = useAuth()

  if (isUserLoading) return <div>Loading...</div>
  if (!user) return <div>Not logged in</div>

  return (
    <div>
      <p>Welcome, {user.email}!</p>
      <button onClick={logout}>Logout</button>
    </div>
  )
}
```

### Login Flow

```tsx
function Login() {
  const { loginMutation } = useAuth()

  const onSubmit = (data: { username: string; password: string }) => {
    loginMutation.mutate(data)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* form fields */}
      {loginMutation.isError && (
        <p className="text-red-600">{loginMutation.error.message}</p>
      )}
      <button disabled={loginMutation.isPending}>
        {loginMutation.isPending ? 'Logging in...' : 'Log In'}
      </button>
    </form>
  )
}
```

### Signup Flow

```tsx
function Signup() {
  const { signUpMutation } = useAuth()

  const onSubmit = (data: { email: string; password: string; full_name?: string }) => {
    signUpMutation.mutate(data)
  }

  // Similar structure to login
}
```

## API Integration

### API Client (src/client/api.ts)

```tsx
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const authApi = {
  login: async (username: string, password: string) => {
    const formData = new URLSearchParams({ username, password })
    const response = await fetch(`${API_URL}/api/v1/login/access-token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    })
    if (!response.ok) throw new Error('Login failed')
    return response.json()
  },

  getCurrentUser: async (token: string) => {
    const response = await fetch(`${API_URL}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) throw new Error('Failed to fetch user')
    return response.json()
  },
}
```

## Form Handling

Use **react-hook-form** with **zod** validation:

```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const formSchema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

type FormData = z.infer<typeof formSchema>

function MyForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(formSchema),
  })

  const onSubmit = (data: FormData) => {
    console.log(data)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} />
      {errors.email && <p className="text-red-600">{errors.email.message}</p>}
    </form>
  )
}
```

## UI Components (shadcn/ui)

### Adding Components

```bash
npx shadcn@latest add button
npx shadcn@latest add input
npx shadcn@latest add dialog
```

### Using Components

```tsx
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

function MyComponent() {
  return (
    <div>
      <Input placeholder="Email" />
      <Button variant="default">Submit</Button>
      <Button variant="outline">Cancel</Button>
    </div>
  )
}
```

## Styling with Tailwind CSS v4

### Standard Colors (Use These)

```tsx
// Background colors
<div className="bg-gray-50">      {/* Light background */}
<div className="bg-gray-900">     {/* Dark background */}
<div className="bg-white">        {/* White background */}

// Text colors
<p className="text-gray-900">     {/* Dark text */}
<p className="text-gray-500">     {/* Muted text */}
<p className="text-red-600">      {/* Error text */}

// Borders
<div className="border border-gray-200">
<div className="border border-gray-300">
```

### Common Patterns

```tsx
// Card
<div className="rounded-lg border border-gray-200 bg-white shadow-sm p-6">

// Button
<button className="bg-gray-900 text-white hover:bg-gray-800 px-4 py-2 rounded-md">

// Input
<input className="border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-gray-400">
```

## State Management

### Server State (TanStack Query)

Already configured in `__root.tsx` with QueryClientProvider.

```tsx
import { useQuery, useMutation } from '@tanstack/react-query'

// Query example
const { data, isLoading } = useQuery({
  queryKey: ['user'],
  queryFn: () => authApi.getCurrentUser(token),
})

// Mutation example
const mutation = useMutation({
  mutationFn: (data) => authApi.login(data.username, data.password),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['user'] })
  },
})
```

### Local State

Use React hooks:
```tsx
const [count, setCount] = useState(0)
const [isOpen, setIsOpen] = useState(false)
```

## Common Patterns

### Loading States

```tsx
if (isUserLoading) {
  return <div className="min-h-screen flex items-center justify-center">
    <p>Loading...</p>
  </div>
}
```

### Error Handling

```tsx
{mutation.isError && (
  <p className="text-sm text-red-600 text-center">
    {mutation.error?.message || 'An error occurred'}
  </p>
)}
```

### Conditional Rendering

```tsx
{user && <p>Welcome, {user.email}</p>}
{!user && <Link to="/login">Log in</Link>}
```

## Troubleshooting

### "Failed to fetch" errors

Check:
1. Backend is running: `curl http://localhost:8000/health`
2. CORS is configured: `FRONTEND_URL=http://localhost:5173` in backend `.env`
3. API URL is correct: `VITE_API_URL=http://localhost:8000` in frontend `.env`

### Routes not working

Regenerate route tree:
```bash
rm -rf src/routeTree.gen.ts
npm run dev
```

### Tailwind not applying

Ensure `src/index.css` is imported in `src/main.tsx`:
```tsx
import './index.css'
```
