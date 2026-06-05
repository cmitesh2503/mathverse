# Frontend Auth Integration Guide

## Files Created
- `src/services/firebaseConfig.ts` — Firebase initialization
- `src/services/AuthContext.tsx` — Auth state management  
- `src/pages/Login.tsx` — Login page (email/password form)
- `src/pages/ForgotPassword.tsx` — Password reset page

## Installation

```bash
npm install firebase
npm install react-router-dom  # if not already installed
```

## Integration Steps

### 1. Configure Firebase

Update `src/services/firebaseConfig.ts` with your Firebase credentials:
- Get from: Firebase Console → Project Settings → Web app config
- Or set environment variables: `REACT_APP_FIREBASE_*`

### 2. Add Routing

Update `src/App.tsx` to import and use BrowserRouter + Routes:

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './services/AuthContext';
import Login from './pages/Login';
import ForgotPassword from './pages/ForgotPassword';
import Home from './pages/Home';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/home" element={<Home />} />
          <Route path="/" element={<Navigate to="/login" />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
```

### 3. Use Auth in Components

```tsx
import { useAuth } from './services/AuthContext';

function MyComponent() {
  const { user, isAuthenticated, loading } = useAuth();
  
  if (loading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" />;
  
  return <div>Welcome, {user?.email}!</div>;
}
```

## Features

### Login Page (`/login`)
- Email/password sign-in via Firebase Auth
- Stores auth token in localStorage
- Redirects to `/home` on success
- Links to password reset and signup

### Forgot Password Page (`/forgot-password`)
- Send Firebase password reset email
- User clicks link in email to reset password
- Firebase handles UI for setting new password
- Redirects to login after success

## How It Works

1. **User signs in** → Firebase Auth validates credentials
2. **Token stored** → ID token saved for backend API requests
3. **Auth state persists** → `onAuthStateChanged` listener keeps user logged in
4. **Protected routes** → Use `useAuth()` hook to check `isAuthenticated` before rendering

## Backend Integration

When calling backend APIs, include the Firebase token:

```tsx
const { user } = useAuth();
const token = await user?.getIdToken();

const response = await axios.get('/api/user/profile', {
  headers: { Authorization: `Bearer ${token}` }
});
```

## Environment Variables (.env.local)

```
REACT_APP_FIREBASE_API_KEY=your_api_key
REACT_APP_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your_project_id
REACT_APP_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
REACT_APP_FIREBASE_APP_ID=your_app_id
```

## Next Steps

- [ ] Update `src/App.tsx` with routing (see Integration Steps)
- [ ] Add Firebase credentials to `.env.local`
- [ ] Install: `npm install react-router-dom`
- [ ] Run: `npm run dev`
- [ ] Test login at `http://localhost:5173/login`
