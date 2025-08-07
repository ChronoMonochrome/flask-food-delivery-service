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
      let telegramUserId = '123';
      if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe && window.Telegram.WebApp.initDataUnsafe.user) {
          telegramUserId = window.Telegram.WebApp.initDataUnsafe.user.id;
      }

      headers.set('X-Telegram-User-ID', telegramUserId);
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