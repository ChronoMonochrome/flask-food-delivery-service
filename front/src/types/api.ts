// API типы для бэкенда
export interface ApiCategory {
  id: string;
  name: string;
  icon: string;
  color: string;
}

export interface ApiNutrition {
  calories: number;
  carbs: number;
  fat: number;
  proteins: number;
}

export interface ApiRecommendation {
  id: string;
  name: string;
  price: number;
  image: string | null;
}

export interface ApiProduct {
  id: string;
  name: string;
  description: string;
  price: number;
  image: string;
  categoryId: string;
  nutrition: ApiNutrition;
  ingredients: string[];
  availableAddons: any[]; // Пока пустой массив
  recommendations: ApiRecommendation[];
}

// Запросы
export interface GetProductsRequest {
  categoryId: string;
}

// --- NEW/UPDATED: DeliveryInfo to match backend's DeliveryInfoNew ---
export interface DeliveryInfo {
  address: string;
  apartment: string | null; // Allow null as per backend
  floor: string | null;     // Allow null as per backend
  phone: string;
  paymentMethod: 'cash' | 'card' | 'online'; // Ensure these match your backend enum
  comment: string | null;   // Allow null as per backend
  // Backend has latitude and longitude directly in DeliveryInfoNew,
  // but frontend handles it separately as 'coordinates' in CheckoutPage state
  // When sending to backend, map `coordinates` array to `latitude` and `longitude`
  // We keep `coordinates` here for frontend state management ease.
  // The POST payload will map `coordinates` to `latitude` and `longitude`.
  coordinates?: [number, number] | null; // For frontend state
}

// --- NEW: OrderItem to match backend's order_item_model ---
export interface OrderItem {
  product: Product; // Or a more specific ApiProduct if you only store essential product details here
  quantity: number;
  selectedAddons: Addon[];
  selectedRecommendations: Recommendation[];
  // If customWok is part of OrderItem in backend, add it here as well
  customWok?: WokCustomization;
}

// --- NEW: Order to match backend's order_model ---
export interface Order {
  id: string;
  items: OrderItem[]; // Use the new OrderItem interface
  total: number;
  deliveryInfo: DeliveryInfo; // Use the new DeliveryInfo interface
  status: 'pending_payment' | 'payment_initiation_failed' | 'payment_succeeded' | 'payment_canceled' | 'waiting_for_capture' | 'iiko_send_failed_exception' | 'pending' | 'preparing' | 'delivering' | 'delivered' | 'cancelled'; // Extend with backend statuses
  createdAt: string; // Backend uses ISO 8601 string for DateTime
  estimatedDelivery?: string | null; // Backend uses ISO 8601 string for DateTime, allow null
  paymentUrl?: string; // Added based on backend's order_model (maps to confirmation_url)
  yookassaPaymentId?: string; // Add if your backend returns this
}
