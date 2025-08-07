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
  quantity?: number;
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
  weight: number;
  nutrition: Nutrition;
  ingredients?: string[];
  availableAddons?: Addon[];
  recommendations?: Recommendation[];
  isCustomizable?: boolean;
}

export interface CartItem {
  product: Product;
  quantity: number;
  selectedAddons: Addon[];
  selectedRecommendations: Recommendation[];
  customWok?: WokCustomization;
}

export interface WokBase {
  id: string;
  name: string;
  price: number;
  image: string;
}

export interface WokMeat {
  id: string;
  name: string;
  price: number;
  image: string;
}

export interface WokTopping {
  id: string;
  name: string;
  price: number;
  image: string;
}

export interface WokSauce {
  id: string;
  name: string;
  price: number;
  image: string;
}

export interface WokCustomization {
  base: WokBase;
  meats: WokMeat[];
  toppings: WokTopping[];
  sauces: WokSauce[];
}

export type Page = 'home' | 'product' | 'wok-builder' | 'cart' | 'checkout' | 'success' | 'orders';
