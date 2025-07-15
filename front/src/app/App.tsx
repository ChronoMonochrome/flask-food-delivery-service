import React from 'react';
import { Provider } from 'react-redux';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { store } from './store';
import { AppRouter } from './router';
import { CartInitializer } from '../entities/cart/components/CartInitializer';
import { theme } from './theme';

function App() {
  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <CartInitializer />
        <AppRouter />
      </ThemeProvider>
    </Provider>
  );
}

export default App;