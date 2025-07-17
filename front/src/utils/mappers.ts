import { ApiCategory, ApiProduct, ApiRecommendation } from '../types/api';
import { Category, Product, Recommendation } from '../types';

// Маппер для категорий
export const mapApiCategoryToCategory = (apiCategory: ApiCategory): Category => ({
  id: apiCategory.id,
  name: apiCategory.name,
  icon: apiCategory.icon,
  color: apiCategory.color,
});

// Маппер для рекомендаций
export const mapApiRecommendationToRecommendation = (apiRec: ApiRecommendation): Recommendation => ({
  id: apiRec.id,
  name: apiRec.name,
  price: apiRec.price,
  image: apiRec.image || 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200', // Fallback изображение
});

// Маппер для продуктов
export const mapApiProductToProduct = (apiProduct: ApiProduct): Product => ({
  id: apiProduct.id,
  name: apiProduct.name,
  description: apiProduct.description,
  price: apiProduct.price,
  image: apiProduct.image,
  categoryId: apiProduct.categoryId,
  weight: 0, // Пока нет в API
  nutrition: {
    calories: apiProduct.nutrition.calories,
    protein: apiProduct.nutrition.proteins, // Маппинг proteins -> protein
    fat: apiProduct.nutrition.fat,
    carbs: apiProduct.nutrition.carbs,
  },
  ingredients: apiProduct.ingredients,
  availableAddons: [], // Пока пустой
  recommendations: apiProduct.recommendations.map(mapApiRecommendationToRecommendation),
});