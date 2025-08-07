import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const BASE_URL = import.meta.env.VITE_APP_API_URL;

export interface GeocodeRequest {
  latitude: number;
  longitude: number;
}

export interface GeocodeResponse {
  delivery_cost: number;
}

export const geocodingApi = createApi({
  reducerPath: 'geocodingApi',
  baseQuery: fetchBaseQuery({
    baseUrl: BASE_URL,
    prepareHeaders: (headers) => {
      const initData = window.Telegram?.WebApp?.initDataUnsafe?.user?.id

      if (initData) {
        headers.set('X-Telegram-Init-Data', initData)
      }
      return headers;
    },
  }),
  tagTypes: ['Geocoding'],
  endpoints: (builder) => ({
    getDeliveryCost: builder.query({
      query: (coordinates) => ({
        url: '/map',
        params:  coordinates ,
      }),
    }),

  }),
});

export const {
  useLazyGetDeliveryCostQuery,
} = geocodingApi;