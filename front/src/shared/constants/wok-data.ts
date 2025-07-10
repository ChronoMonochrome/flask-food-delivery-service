import { WokBase, WokMeat, WokTopping, WokSauce, Product } from '../types';

export const wokBases: WokBase[] = [
  { id: 'rice', name: 'Рис', price: 0, image: 'https://images.pexels.com/photos/723198/pexels-photo-723198.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'buckwheat', name: 'Гречневая лапша', price: 0, image: 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'wheat', name: 'Пшеничная лапша', price: 0, image: 'https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'glass', name: 'Стеклянная лапша', price: 0, image: 'https://images.pexels.com/photos/1640774/pexels-photo-1640774.jpeg?auto=compress&cs=tinysrgb&w=200' }
];

export const wokMeats: WokMeat[] = [
  { id: 'chicken', name: 'Курица', price: 120, image: 'https://images.pexels.com/photos/616354/pexels-photo-616354.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'beef', name: 'Говядина', price: 180, image: 'https://images.pexels.com/photos/361184/asparagus-steak-veal-steak-veal-361184.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'pork', name: 'Свинина', price: 150, image: 'https://images.pexels.com/photos/323682/pexels-photo-323682.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'shrimp', name: 'Креветки', price: 220, image: 'https://images.pexels.com/photos/566345/pexels-photo-566345.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'tofu', name: 'Тофу', price: 100, image: 'https://images.pexels.com/photos/4518843/pexels-photo-4518843.jpeg?auto=compress&cs=tinysrgb&w=200' }
];

export const wokToppings: WokTopping[] = [
  { id: 'mushrooms', name: 'Грибы', price: 80, image: 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'broccoli', name: 'Брокколи', price: 60, image: 'https://images.pexels.com/photos/47347/broccoli-vegetable-food-healthy-47347.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'peppers', name: 'Болгарский перец', price: 50, image: 'https://images.pexels.com/photos/128536/pexels-photo-128536.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'bamboo', name: 'Побеги бамбука', price: 70, image: 'https://images.pexels.com/photos/1640774/pexels-photo-1640774.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'corn', name: 'Кукуруза', price: 40, image: 'https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'carrots', name: 'Морковь', price: 30, image: 'https://images.pexels.com/photos/143133/pexels-photo-143133.jpeg?auto=compress&cs=tinysrgb&w=200' }
];

export const wokSauces: WokSauce[] = [
  { id: 'teriyaki', name: 'Терияки', price: 60, image: 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'sweet-sour', name: 'Кисло-сладкий', price: 60, image: 'https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'spicy', name: 'Острый', price: 60, image: 'https://images.pexels.com/photos/1640774/pexels-photo-1640774.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'garlic', name: 'Чесночный', price: 60, image: 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200' }
];

export const wokBuilderProduct: Product = {
  id: 'wok-builder',
  name: 'Собери свою коробочку',
  description: 'Создай свой уникальный WOK! Выбери основу, добавь мясо и начинки по вкусу',
  price: 210,
  image: 'https://images.pexels.com/photos/1640774/pexels-photo-1640774.jpeg?auto=compress&cs=tinysrgb&w=400',
  categoryId: '9',
  weight: 330,
  nutrition: { calories: 250, protein: 8, fat: 5, carbs: 45 },
  ingredients: ['основа', 'овощи', 'соус'],
  isCustomizable: true,
  recommendations: [
    { id: 'cola', name: 'Кола 0.5л', price: 120, image: 'https://images.pexels.com/photos/50593/coca-cola-cold-drink-soft-drink-coke-50593.jpeg?auto=compress&cs=tinysrgb&w=200' },
    { id: 'fries', name: 'Картофель фри', price: 180, image: 'https://images.pexels.com/photos/1583884/pexels-photo-1583884.jpeg?auto=compress&cs=tinysrgb&w=200' },
    { id: 'onion-rings', name: 'Луковые кольца', price: 220, image: 'https://images.pexels.com/photos/4518843/pexels-photo-4518843.jpeg?auto=compress&cs=tinysrgb&w=200' }
  ]
};