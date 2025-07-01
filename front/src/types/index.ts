export interface Category {
  id: string;
  name: string;
  icon: string;
  color: string;
}

export interface Nutrition {
  calories: number;
  protein: number;
  fat: number;
  carbs: number;
}

export interface Addon {
  id: string;
  name: string;
  price: number;
}

export interface Recommendation {
  id: string;
  name: string;
  price: number;
  image: string;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  image: string;
  categoryId: string;
  nutrition: Nutrition;
  ingredients?: string[];
  availableAddons?: Addon[];
  recommendations?: Recommendation[];
}

export interface CartItem {
  product: Product;
  quantity: number;
  selectedAddons: Addon[];
  selectedRecommendations: Recommendation[];
}

export interface DeliveryInfo {
  address: string;
  phone: string;
  paymentMethod: 'cash' | 'card' | 'online';
  comment: string;
}

export interface Order {
  id: string;
  items: CartItem[];
  total: number;
  deliveryInfo: DeliveryInfo;
  status: 'pending' | 'preparing' | 'delivering' | 'delivered' | 'cancelled';
  createdAt: Date;
  estimatedDelivery?: Date;
}