import { Category, Product, Addon, Recommendation, Order } from '../types';

export const categories: Category[] = [
  { id: '1', name: 'Пицца', icon: '🍕', color: 'from-red-400 to-red-600' },
  { id: '2', name: 'Бургеры', icon: '🍔', color: 'from-yellow-400 to-orange-500' },
  { id: '3', name: 'Суши', icon: '🍣', color: 'from-green-400 to-teal-500' },
  { id: '4', name: 'Салаты', icon: '🥗', color: 'from-green-300 to-green-500' },
  { id: '5', name: 'Десерты', icon: '🍰', color: 'from-pink-400 to-purple-500' },
  { id: '6', name: 'Напитки', icon: '🥤', color: 'from-blue-400 to-cyan-500' },
  { id: '7', name: 'Закуски', icon: '🍟', color: 'from-orange-400 to-red-500' },
  { id: '8', name: 'Горячее', icon: '🍲', color: 'from-amber-400 to-orange-600' },
  { id: '9', name: 'WOK', icon: '🥢', color: 'from-red-500 to-orange-600' },
];

const commonAddons: Addon[] = [
  { id: 'ketchup', name: 'Кетчуп', price: 15 },
  { id: 'mayo', name: 'Майонез', price: 15 },
  { id: 'mustard', name: 'Горчица', price: 15 },
  { id: 'soy', name: 'Соевый соус', price: 20 },
];

const commonRecommendations: Recommendation[] = [
  { id: 'cola', name: 'Кола 0.5л', price: 120, image: 'https://images.pexels.com/photos/50593/coca-cola-cold-drink-soft-drink-coke-50593.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'fries', name: 'Картофель фри', price: 180, image: 'https://images.pexels.com/photos/1583884/pexels-photo-1583884.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'onion-rings', name: 'Луковые кольца', price: 220, image: 'https://images.pexels.com/photos/4518843/pexels-photo-4518843.jpeg?auto=compress&cs=tinysrgb&w=200' },
];

export const products: Product[] = [
  {
    id: '1',
    name: 'Маргарита',
    description: 'Классическая пицца с томатным соусом, моцареллой и базиликом',
    price: 590,
    image: 'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=400',
    categoryId: '1',
    weight: 450,
    nutrition: { calories: 250, protein: 12, fat: 10, carbs: 30 },
    ingredients: ['тесто', 'томатный соус', 'моцарелла', 'базилик', 'оливковое масло'],
    availableAddons: commonAddons.slice(0, 2),
    recommendations: commonRecommendations
  },
  {
    id: '2',
    name: 'Пепперони',
    description: 'Пицца с острой колбасой пепперони и сыром моцарелла',
    price: 690,
    image: 'https://images.pexels.com/photos/845812/pexels-photo-845812.jpeg?auto=compress&cs=tinysrgb&w=400',
    categoryId: '1',
    weight: 480,
    nutrition: { calories: 320, protein: 15, fat: 18, carbs: 28 },
    ingredients: ['тесто', 'томатный соус', 'моцарелла', 'пепперони'],
    availableAddons: commonAddons.slice(0, 3),
    recommendations: commonRecommendations
  },
  {
    id: '3',
    name: 'Классический бургер',
    description: 'Сочная говяжья котлета с салатом, помидором и специальным соусом',
    price: 450,
    image: 'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=400',
    categoryId: '2',
    weight: 320,
    nutrition: { calories: 380, protein: 22, fat: 20, carbs: 25 },
    ingredients: ['булочка', 'говяжья котлета', 'салат', 'помидор', 'соус'],
    availableAddons: commonAddons,
    recommendations: commonRecommendations
  },
  {
    id: '4',
    name: 'Чизбургер',
    description: 'Бургер с сыром чеддер, котлетой и овощами',
    price: 520,
    image: 'https://images.pexels.com/photos/552056/pexels-photo-552056.jpeg?auto=compress&cs=tinysrgb&w=400',
    categoryId: '2',
    weight: 350,
    nutrition: { calories: 420, protein: 25, fat: 24, carbs: 26 },
    ingredients: ['булочка', 'котлета', 'сыр чеддер', 'салат', 'огурцы'],
    availableAddons: commonAddons,
    recommendations: commonRecommendations
  },
  {
    id: '5',
    name: 'Сет Филадельфия',
    description: 'Роллы с лососем, сливочным сыром и огурцом',
    price: 890,
    image: 'https://images.pexels.com/photos/357756/pexels-photo-357756.jpeg?auto=compress&cs=tinysrgb&w=400',
    categoryId: '3',
    weight: 280,
    nutrition: { calories: 180, protein: 8, fat: 12, carbs: 15 },
    ingredients: ['рис', 'нори', 'лосось', 'сливочный сыр', 'огурец'],
    availableAddons: [commonAddons[3]],
    recommendations: [commonRecommendations[0]]
  },
  {
    id: '6',
    name: 'Цезарь с курицей',
    description: 'Свежий салат с курицей, пармезаном и соусом цезарь',
    price: 380,
    image: 'https://images.pexels.com/photos/1059905/pexels-photo-1059905.jpeg?auto=compress&cs=tinysrgb&w=400',
    categoryId: '4',
    weight: 250,
    nutrition: { calories: 220, protein: 18, fat: 12, carbs: 8 },
    ingredients: ['салат романо', 'куриная грудка', 'пармезан', 'соус цезарь', 'сухарики'],
    availableAddons: commonAddons.slice(0, 2),
    recommendations: [commonRecommendations[0]]
  },
  {
    id: '7',
    name: 'Тирамису',
    description: 'Классический итальянский десерт с кофе и маскарпоне',
    price: 290,
    image: 'https://images.pexels.com/photos/6880219/pexels-photo-6880219.jpeg?auto=compress&cs=tinysrgb&w=400',
    categoryId: '5',
    weight: 150,
    nutrition: { calories: 350, protein: 6, fat: 22, carbs: 32 },
    ingredients: ['маскарпоне', 'печенье савоярди', 'кофе', 'какао'],
    recommendations: [commonRecommendations[0]]
  },
  {
    id: '8',
    name: 'Кола 0.5л',
    description: 'Освежающий газированный напиток',
    price: 120,
    image: 'https://images.pexels.com/photos/50593/coca-cola-cold-drink-soft-drink-coke-50593.jpeg?auto=compress&cs=tinysrgb&w=400',
    categoryId: '6',
    weight: 500,
    nutrition: { calories: 42, protein: 0, fat: 0, carbs: 10.6 }
  },
  // WOK товары
  {
    id: '9',
    name: 'WOK с курицей терияки',
    description: 'Лапша удон с курицей в соусе терияки, овощами и кунжутом',
    price: 450,
    image: 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=400',
    categoryId: '9',
    weight: 350,
    nutrition: { calories: 380, protein: 25, fat: 12, carbs: 45 },
    ingredients: ['лапша удон', 'куриная грудка', 'соус терияки', 'болгарский перец', 'морковь', 'кунжут'],
    availableAddons: [commonAddons[3]],
    recommendations: commonRecommendations
  },
  {
    id: '10',
    name: 'WOK с говядиной',
    description: 'Рисовая лапша с говядиной, овощами в остром соусе',
    price: 520,
    image: 'https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg?auto=compress&cs=tinysrgb&w=400',
    categoryId: '9',
    weight: 380,
    nutrition: { calories: 420, protein: 28, fat: 15, carbs: 42 },
    ingredients: ['рисовая лапша', 'говядина', 'острый соус', 'брокколи', 'лук', 'чеснок'],
    availableAddons: [commonAddons[3]],
    recommendations: commonRecommendations
  },
  {
    id: '11',
    name: 'Собери свою коробочку',
    description: 'Создай свой уникальный WOK! Выбери основу, добавь мясо и начинки по вкусу',
    price: 210, // Базовая цена за основу
    image: 'https://images.pexels.com/photos/1640774/pexels-photo-1640774.jpeg?auto=compress&cs=tinysrgb&w=400',
    categoryId: '9',
    weight: 330,
    nutrition: { calories: 250, protein: 8, fat: 5, carbs: 45 },
    ingredients: ['основа', 'овощи', 'соус'],
    isCustomizable: true, // Специальный флаг для конструктора
    recommendations: commonRecommendations // Добавляем рекомендации для базового товара
  }
];

export const mockOrders: Order[] = [
  {
    id: '1',
    items: [
      {
        product: products[0],
        quantity: 1,
        selectedAddons: [commonAddons[0]],
        selectedRecommendations: [commonRecommendations[0]]
      }
    ],
    total: 725,
    deliveryInfo: {
      address: 'ул. Пушкина, д. 10, кв. 5',
      phone: '+7 (999) 123-45-67',
      paymentMethod: 'cash',
      comment: 'Домофон не работает'
    },
    status: 'delivering',
    createdAt: new Date(Date.now() - 30 * 60 * 1000),
    estimatedDelivery: new Date(Date.now() + 15 * 60 * 1000)
  },
  {
    id: '2',
    items: [
      {
        product: products[2],
        quantity: 2,
        selectedAddons: [],
        selectedRecommendations: [commonRecommendations[1]]
      }
    ],
    total: 1080,
    deliveryInfo: {
      address: 'пр. Ленина, д. 25',
      phone: '+7 (999) 987-65-43',
      paymentMethod: 'card',
      comment: ''
    },
    status: 'delivered',
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000)
  }
];

// Данные для конструктора WOK
export const wokBases = [
  { id: 'rice', name: 'Рис', price: 0, image: 'https://images.pexels.com/photos/723198/pexels-photo-723198.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'buckwheat', name: 'Гречневая лапша', price: 0, image: 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'wheat', name: 'Пшеничная лапша', price: 0, image: 'https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'glass', name: 'Стеклянная лапша', price: 0, image: 'https://images.pexels.com/photos/1640774/pexels-photo-1640774.jpeg?auto=compress&cs=tinysrgb&w=200' }
];

export const wokMeats = [
  { id: 'chicken', name: 'Курица', price: 120, image: 'https://images.pexels.com/photos/616354/pexels-photo-616354.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'beef', name: 'Говядина', price: 180, image: 'https://images.pexels.com/photos/361184/asparagus-steak-veal-steak-veal-361184.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'pork', name: 'Свинина', price: 150, image: 'https://images.pexels.com/photos/323682/pexels-photo-323682.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'shrimp', name: 'Креветки', price: 220, image: 'https://images.pexels.com/photos/566345/pexels-photo-566345.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'tofu', name: 'Тофу', price: 100, image: 'https://images.pexels.com/photos/4518843/pexels-photo-4518843.jpeg?auto=compress&cs=tinysrgb&w=200' }
];

export const wokToppings = [
  { id: 'mushrooms', name: 'Грибы', price: 80, image: 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'broccoli', name: 'Брокколи', price: 60, image: 'https://images.pexels.com/photos/47347/broccoli-vegetable-food-healthy-47347.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'peppers', name: 'Болгарский перец', price: 50, image: 'https://images.pexels.com/photos/128536/pexels-photo-128536.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'bamboo', name: 'Побеги бамбука', price: 70, image: 'https://images.pexels.com/photos/1640774/pexels-photo-1640774.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'corn', name: 'Кукуруза', price: 40, image: 'https://images.pexels.com/photos/1玉米/pexels-photo-1640772.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'carrots', name: 'Морковь', price: 30, image: 'https://images.pexels.com/photos/143133/pexels-photo-143133.jpeg?auto=compress&cs=tinysrgb&w=200' }
];

export const wokSauces = [
  { id: 'teriyaki', name: 'Терияки', price: 60, image: 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'sweet-sour', name: 'Кисло-сладкий', price: 60, image: 'https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'spicy', name: 'Острый', price: 60, image: 'https://images.pexels.com/photos/1640774/pexels-photo-1640774.jpeg?auto=compress&cs=tinysrgb&w=200' },
  { id: 'garlic', name: 'Чесночный', price: 60, image: 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=200' }
];