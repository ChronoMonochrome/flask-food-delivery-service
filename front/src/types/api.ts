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