import { ApiCategory, ApiProduct, ApiRecommendation } from '../api/types';
import { Category, Product, Recommendation, Addon } from '../types';

const safeNumber = (value: any, fallback: number = 0): number => {
  if (typeof value === 'number' && !isNaN(value)) {
    return value;
  }
  return fallback;
};

const safeString = (value: any, fallback: string = ''): string => {
  if (typeof value === 'string') {
    return value;
  }
  if (value && typeof value === 'object' && value.name) {
    return String(value.name);
  }
  if (value && typeof value === 'object' && value.code) {
    return String(value.code);
  }
  return String(value || fallback);
};

export const mapApiCategoryToCategory = (apiCategory: ApiCategory): Category => ({
  id: safeString(apiCategory?.id),
  name: safeString(apiCategory?.name),
  icon: safeString(apiCategory?.icon),
  color: safeString(apiCategory?.color),
});

export const mapApiRecommendationToRecommendation = (apiRec: ApiRecommendation): Recommendation => ({
  id: safeString(apiRec?.id),
  name: safeString(apiRec?.name),
  price: safeNumber(apiRec?.price),
  image: safeString(apiRec?.image) || 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200',
});

export const mapApiAddonToAddon = (apiAddon: any): Addon => ({
  id: safeString(apiAddon?.id),
  name: safeString(apiAddon?.name),
  price: safeNumber(apiAddon?.price),
});
export const mapApiProductToProduct = (apiProduct: ApiProduct): Product => ({
  id: safeString(apiProduct?.id),
  name: safeString(apiProduct?.name),
  description: safeString(apiProduct?.description),
  price: safeNumber(apiProduct?.price),
  image: safeString(apiProduct?.image),
  categoryId: safeString(apiProduct?.categoryId),
  weight: 0,
  nutrition: {
    calories: safeNumber(apiProduct?.nutrition?.calories),
    protein: safeNumber(apiProduct?.nutrition?.proteins),
    fat: safeNumber(apiProduct?.nutrition?.fat),
    carbs: safeNumber(apiProduct?.nutrition?.carbs),
  },
  ingredients: Array.isArray(apiProduct?.ingredients) 
    ? apiProduct.ingredients.map(ingredient => safeString(ingredient))
    : [],
  availableAddons: Array.isArray(apiProduct?.availableAddons) 
    ? apiProduct.availableAddons.map(mapApiAddonToAddon)
    : [],
  recommendations: Array.isArray(apiProduct?.recommendations) 
    ? apiProduct.recommendations.map(mapApiRecommendationToRecommendation)
    : [],
});