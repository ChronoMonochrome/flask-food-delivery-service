import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { ApiCategory, ApiProduct, GetProductsRequest } from '../types/api';

const BASE_URL = 'https://mandarin.dev.routeam.ru/api';

export const api = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: BASE_URL,
  }),
  tagTypes: ['Category', 'Product'],
  endpoints: (builder) => ({
    // Получение категорий
    getCategories: builder.query<ApiCategory[], void>({
      query: () => '/categories',
      providesTags: ['Category'],
    }),
    
    // Получение продуктов по категории
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