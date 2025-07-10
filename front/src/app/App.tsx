import React from 'react';
import { Provider } from 'react-redux';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { store } from './store';
import { theme } from './theme';
import { AppRouter } from './router';
import { CartInitializer } from '../entities/cart/components/CartInitializer';

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