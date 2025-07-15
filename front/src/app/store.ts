import { configureStore } from '@reduxjs/toolkit';
import { api } from '../shared/api';
import { backendCartSlice } from '../entities/cart';
import { cartApi } from '../shared/api/cart-api';
import { navigationSlice } from '../features/navigation';

export const store = configureStore({
  reducer: {
    [api.reducerPath]: api.reducer,
    [cartApi.reducerPath]: cartApi.reducer,
    backendCart: backendCartSlice.reducer,
    navigation: navigationSlice.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware()
      .concat(api.middleware)
      .concat(cartApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;