import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, process.cwd(), '')

    return {
        plugins: [react()],
        server: {
            port: 5174,
            proxy: {
                // In development, proxy /api calls to local Django backend on :8000
                '/api': {
                    target: 'http://localhost:8000',
                    changeOrigin: true,
                }
            }
        },
        build: {
            outDir: 'dist',
            sourcemap: false,
            chunkSizeWarningLimit: 1000,
            rollupOptions: {
                output: {
                    manualChunks: {
                        vendor: ['react', 'react-dom', 'react-router-dom'],
                        charts: ['recharts'],
                        toast: ['react-hot-toast'],
                    }
                }
            }
        }
    }
})
