import React from 'react';
import { 
  Box, 
  Chip, 
  Typography,
  Stack
} from '@mui/material';
import { Category } from '../../shared/types';

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
    <Box py={1.5} px={2}>
      <Stack 
        direction="row" 
        spacing={1} 
        sx={{ 
          overflowX: 'auto',
          '&::-webkit-scrollbar': { display: 'none' },
          scrollbarWidth: 'none',
          pb: 0.5, // Небольшой отступ снизу для тени
        }}
      >
        {categories.map((category) => (
          <Chip
            key={category.id}
            label={
              <Box display="flex" flexDirection="column" alignItems="center" py={0.5}>
                <Typography 
                  variant="h6" 
                  component="div" 
                  sx={{ 
                    fontSize: '1.25rem', 
                    mb: 0.25,
                    filter: selectedCategory === category.id ? 'none' : 'grayscale(0.3)',
                    transition: 'filter 0.2s ease'
                  }}
                >
                  {category.icon}
                </Typography>
                <Typography 
                  variant="caption" 
                  sx={{ 
                    fontSize: '0.7rem', 
                    textAlign: 'center', 
                    lineHeight: 1.1,
                    fontWeight: selectedCategory === category.id ? 600 : 400,
                    transition: 'font-weight 0.2s ease'
                  }}
                >
                  {category.name}
                </Typography>
              </Box>
            }
            onClick={() => onCategorySelect(category.id)}
            variant={selectedCategory === category.id ? 'filled' : 'outlined'}
            sx={{
              minWidth: 70,
              height: 80,
              borderRadius: 1.5, // Уменьшенные скругления
              border: selectedCategory === category.id ? 'none' : '1px solid #4B5563',
              backgroundColor: selectedCategory === category.id 
                ? 'primary.main'
                : 'background.paper',
              color: selectedCategory === category.id ? 'white' : 'text.primary',
              boxShadow: selectedCategory === category.id 
                ? '0 2px 8px rgba(234, 181, 69, 0.3)' 
                : '0 1px 3px rgba(0, 0, 0, 0.1)',
              transition: 'all 0.2s ease',
              '&:hover': {
                backgroundColor: selectedCategory === category.id 
                  ? 'primary.dark'
                  : 'rgba(107, 114, 128, 0.05)',
                transform: 'translateY(-1px)',
                boxShadow: selectedCategory === category.id 
                  ? '0 4px 12px rgba(234, 181, 69, 0.4)' 
                  : '0 2px 6px rgba(0, 0, 0, 0.15)',
              },
              '&:active': {
                transform: 'translateY(0)',
              },
              '& .MuiChip-label': {
                padding: 0,
              },
            }}
          />
        ))}
      </Stack>
    </Box>
  );
};