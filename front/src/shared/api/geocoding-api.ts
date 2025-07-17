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
      headers.set('X-Telegram-User-ID', '123');
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