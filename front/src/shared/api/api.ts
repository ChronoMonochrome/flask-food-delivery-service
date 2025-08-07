import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { ApiCategory, ApiProduct, GetProductsRequest } from './types';

const BASE_URL = import.meta.env.VITE_APP_API_URL;

export const api = createApi({
  reducerPath: 'api',
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
  tagTypes: ['Category', 'Product'],
  endpoints: (builder) => ({
    getCategories: builder.query<ApiCategory[], void>({
      query: () => '/categories',
      providesTags: ['Category'],
    }),
    
    getProducts: builder.query<ApiProduct[], GetProductsRequest>({
      query: ({ categoryId }) => ({
        url: '/products',
        params: { categoryId },
      }),
      providesTags: (result, error, { categoryId }) => [
        { type: 'Product', id: categoryId },
      ],
    }),
  }),
});

export const {
  useGetCategoriesQuery,
  useGetProductsQuery,
} = api;