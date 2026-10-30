import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The backend's CORS allows only http://localhost:3000, so the port and host are fixed.
export default defineConfig({
  plugins: [react()],
  server: { host: 'localhost', port: 3000, strictPort: true },
  preview: { host: 'localhost', port: 3000, strictPort: true },
})
