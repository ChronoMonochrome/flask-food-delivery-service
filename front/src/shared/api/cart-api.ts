// front/src/shared/api/cart-api.ts
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const BASE_URL = import.meta.env.VITE_APP_API_URL;

export interface BackendCartItem {
  id: string;
  productId: string;
  quantity: number;
  selectedAddons: Array<{
    id: string;
    quantity: number;
  }>;
  selectedRecommendations: string[];
  customWok?: {
    baseId: string;
    meatIds: string[];
    toppingIds: string[];
    sauceIds: string[];
  };
}

export interface BackendCart {
  items: BackendCartItem[];
  total: number;
}

export interface AddToCartRequest {
  productId: string;
  quantity?: number;
  addons?: Array<{
    id: string;
    quantity: number;
  }>;
  recommendations?: string[];
  customWok?: {
    baseId: string;
    meatIds: string[];
    toppingIds: string[];
    sauceIds: string[];
  };
  // Дополнительные поля для кастомных товаров
  customName?: string;
  customDescription?: string;
  customPrice?: number;
}

export interface UpdateCartItemRequest {
  itemId: string;
  quantity: number;
}

export interface RemoveFromCartRequest {
  itemId: string;
}

export const cartApi = createApi({
  reducerPath: 'cartApi',
  baseQuery: fetchBaseQuery({
    baseUrl: BASE_URL,
    prepareHeaders: (headers) => {
      let telegramUserId = ''

      if (
          window.Telegram &&
          window.Telegram.WebApp &&
          window.Telegram.WebApp.initDataUnsafe &&
          window.Telegram.WebApp.initDataUnsafe.user
      ) {
        telegramUserId = window.Telegram.WebApp.initDataUnsafe.user.id
      }

      headers.set('X-Telegram-User-ID', telegramUserId)

      return headers
    }
  }),
  tagTypes: ['Cart'],
  endpoints: (builder) => ({
    getCart: builder.query<BackendCart, void>({
      query: () => '/cart',
      providesTags: ['Cart'],
    }),

    addToCart: builder.mutation<BackendCart, AddToCartRequest>({
      query: (body) => ({
        url: '/cart/add',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Cart'],
    }),

    updateCartItem: builder.mutation<BackendCart, UpdateCartItemRequest>({
      query: (body) => ({
        url: '/cart/update',
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Cart'],
    }),

    removeFromCart: builder.mutation<BackendCart, RemoveFromCartRequest>({
      query: (body) => ({
        url: '/cart/remove',
        method: 'DELETE',
        body,
      }),
      invalidatesTags: ['Cart'],
    }),

    clearCart: builder.mutation<void, void>({
      query: () => ({
        url: '/cart/clear',
        method: 'DELETE',
      }),
      // FIX: Add transformResponse to explicitly return undefined for a void response
      // This helps RTK Query properly handle cases where the backend might send
      // a 200 OK with an empty body, which could otherwise be interpreted
      // in a way that causes the 'invalidatesTags' error.
      transformResponse: () => undefined,
      invalidatesTags: ['Cart'],
    }),
  }),
});

export const {
  useGetCartQuery,
  useAddToCartMutation,
  useUpdateCartItemMutation,
  useRemoveFromCartMutation,
  useClearCartMutation,
} = cartApi;