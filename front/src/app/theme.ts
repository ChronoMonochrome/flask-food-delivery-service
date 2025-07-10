import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#EAB545', // mandarin-orange
      light: '#F5C76B',
      dark: '#D4A332',
    },
    secondary: {
      main: '#F59E0B', // yellow-500
      light: '#FCD34D',
      dark: '#D97706',
    },
    background: {
      default: '#1D1D1B', // mandarin-bg
      paper: '#2C2C2A', // mandarin-card
    },
    surface: {
      main: '#3A3A37', // mandarin-card-light
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#9CA3AF', // gray-400
    },
    error: {
      main: '#EF4444',
    },
    warning: {
      main: '#F59E0B',
    },
    info: {
      main: '#3B82F6',
    },
    success: {
      main: '#10B981',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: {
      fontSize: '2rem',
      fontWeight: 700,
    },
    h2: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.5,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.43,
    },
  },
  shape: {
    borderRadius: 16,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          textTransform: 'none',
          fontWeight: 600,
          padding: '12px 24px',
        },
        contained: {
          background: 'linear-gradient(45deg, #EAB545 30%, #F59E0B 90%)',
          '&:hover': {
            background: 'linear-gradient(45deg, #F59E0B 30%, #EAB545 90%)',
            transform: 'scale(1.02)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#2C2C2A',
          borderRadius: 16,
          border: '1px solid #4B5563',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: '#374151',
            borderRadius: 12,
            '& fieldset': {
              borderColor: '#4B5563',
            },
            '&:hover fieldset': {
              borderColor: '#6B7280',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#EAB545',
            },
          },
        },
      },
    },
  },
});

// Расширяем тему для кастомных цветов
declare module '@mui/material/styles' {
  interface Palette {
    surface: Palette['primary'];
  }

  interface PaletteOptions {
    surface?: PaletteOptions['primary'];
  }
}