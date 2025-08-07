import { configureStore } from '@reduxjs/toolkit';
import { api } from '../store/api';
import { backendCartSlice } from '../entities/cart';
import { cartApi } from '../shared/api/cart-api';
import { wokApi } from '../shared/api/wok-api';
import { geocodingApi } from '../shared/api/geocoding-api';
import { navigationSlice } from '../features/navigation';

export const store = configureStore({
  reducer: {
    [api.reducerPath]: api.reducer,
    [cartApi.reducerPath]: cartApi.reducer,
    [wokApi.reducerPath]: wokApi.reducer,
    [geocodingApi.reducerPath]: geocodingApi.reducer,
    backendCart: backendCartSlice.reducer,
    navigation: navigationSlice.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware()
      .concat(api.middleware)
      .concat(cartApi.middleware)
      .concat(wokApi.middleware)
      .concat(geocodingApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
