import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { ApiCategory, ApiProduct, GetProductsRequest } from '../types/api';
// We no longer need Order and DeliveryInfo types directly for the *input* payload of createOrder,
// as the backend retrieves cart items internally and expects a flat delivery info.
// Keep Order for the GET /orders/:id/status endpoint.
import { Order } from '../types';

const BASE_URL = '/api';

// Define the precise payload structure the backend expects for POST /api/orders
// This corresponds to your backend's request_order_payload_model
interface CreateOrderBackendPayload {
  address: string;
  apartment: string | null;
  floor: string | null;
  phone: string;
  comment: string | null;
  latitude: number | null;
  longitude: number | null;
  paymentMethod: 'cash' | 'card' | 'online'; // Ensure these match your backend enum
  // No 'items', 'totalAmount', 'deliveryCost' here, as backend derives them
}

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
  tagTypes: ['Category', 'Product', 'Order'],
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

    // --- REVISED createOrder MUTATION ---
    createOrder: builder.mutation<
      { orderId: string; paymentUrl?: string },
      // The input type should now directly match CreateOrderBackendPayload
      CreateOrderBackendPayload
    >({
      query: (orderData) => ({ // orderData is now of type CreateOrderBackendPayload
        url: '/orders',
        method: 'POST',
        body: {
          // Pass the orderData object directly, as it now matches the backend's expectation
          ...orderData,
        },
      }),
      invalidatesTags: ['Order'], // This should now be correctly recognized
    }),

    getOrderStatus: builder.query<Order, string>({
      query: (orderId) => `/orders/${orderId}/status`,
      providesTags: (result, error, orderId) => [{ type: 'Order', id: orderId }],
    }),
  }),
});

export const {
  useGetCategoriesQuery,
  useGetProductsQuery,
  useCreateOrderMutation,
  useGetOrderStatusQuery,
} = api;
