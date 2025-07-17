import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const BASE_URL = import.meta.env.VITE_APP_API_URL;

export interface WokAddon {
  group_name: string;
  id: string;
  image: string | null;
  name: string;
  price: number;
}

export const wokApi = createApi({
  reducerPath: 'wokApi',
  baseQuery: fetchBaseQuery({
    baseUrl: BASE_URL,
    prepareHeaders: (headers) => {
      headers.set('X-Telegram-User-ID', '123');
      return headers;
    },
  }),
  tagTypes: ['WokAddons'],
  endpoints: (builder) => ({
    getWokAddonsByGroup: builder.query<WokAddon[], string>({
      query: (groupName) => `/addons/by_group_name/${groupName}`,
      providesTags: (result, error, groupName) => [
        { type: 'WokAddons', id: groupName },
      ],
    }),
  }),
});

export const {
  useGetWokAddonsByGroupQuery,
} = wokApi;