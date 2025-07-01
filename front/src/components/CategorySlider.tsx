import React from 'react';
import { Category } from '../types';

interface CategorySliderProps {
  categories: Category[];
  selectedCategory: string;
  onCategorySelect: (categoryId: string) => void;
}

export const CategorySlider: React.FC<CategorySliderProps> = ({
  categories,
  selectedCategory,
  onCategorySelect
}) => {
  return (
    <div className="py-4 px-4">
      <div className="flex space-x-3 overflow-x-auto scrollbar-hide">
        {categories.map((category) => (
          <button
            key={category.id}
            onClick={() => onCategorySelect(category.id)}
            className={`
              flex-shrink-0 flex flex-col items-center p-3 rounded-2xl transition-all duration-200
              ${selectedCategory === category.id
                ? 'bg-gradient-to-br from-mandarin-orange to-yellow-500 text-white shadow-lg transform scale-105'
                : 'bg-mandarin-card text-gray-300 hover:bg-gray-700 shadow-md border border-gray-600'
              }
            `}
          >
            <div className={`
              w-12 h-12 flex items-center justify-center rounded-xl text-2xl mb-2
              ${selectedCategory === category.id
                ? 'bg-white/20'
                : `bg-gradient-to-br ${category.color}`
              }
            `}>
              {category.icon}
            </div>
            <span className="text-xs font-medium whitespace-nowrap">
              {category.name}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};