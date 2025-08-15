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

interface OrderRequest {
	address: string,
	apartment: string,
	floor: string,
	phone: string,
	paymentMethod: 'cash' | 'card' | 'online',
	comment: string
	latitude?: number,
	longitude?: number
}

export const orderApi = createApi({
	reducerPath: 'orderApi',
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
	tagTypes: ['Order'],
	endpoints: (builder) => ({
		getOrders: builder.query<BackendCart, void>({
			query: () => '/orders',
			providesTags: ['Order'],
		}),
		addOrder: builder.mutation<BackendCart, OrderRequest>({
			query: (body) => ({
				url: '/orders',
				method: 'POST',
				body,
			}),
			invalidatesTags: ['Order'],
		}),
	}),
});

export const {
	useAddOrderMutation,
	useGetOrdersQuery
} = orderApi;