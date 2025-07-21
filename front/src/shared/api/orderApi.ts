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
	reducerPath: 'cartApi',
	baseQuery: fetchBaseQuery({
		baseUrl: BASE_URL,
		prepareHeaders: (headers) => {
			headers.set('X-Telegram-User-ID', '123');
			return headers;
		},
	}),
	tagTypes: ['Order'],
	endpoints: (builder) => ({
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
} = orderApi;