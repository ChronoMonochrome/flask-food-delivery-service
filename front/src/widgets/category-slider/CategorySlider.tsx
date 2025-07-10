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
    <Box py={2} px={2}>
      <Stack 
        direction="row" 
        spacing={1.5} 
        sx={{ 
          overflowX: 'auto',
          '&::-webkit-scrollbar': { display: 'none' },
          scrollbarWidth: 'none',
        }}
      >
        {categories.map((category) => (
          <Chip
            key={category.id}
            label={
              <Box display="flex" flexDirection="column" alignItems="center" py={1}>
                <Typography variant="h6" component="div" sx={{ fontSize: '1.5rem', mb: 0.5 }}>
                  {category.icon}
                </Typography>
                <Typography variant="caption" sx={{ fontSize: '0.75rem', textAlign: 'center', lineHeight: 1.2 }}>
                  {category.name}
                </Typography>
              </Box>
            }
            onClick={() => onCategorySelect(category.id)}
            variant={selectedCategory === category.id ? 'filled' : 'outlined'}
            sx={{
              minWidth: 80,
              height: 96,
              borderRadius: 2,
              border: selectedCategory === category.id ? 'none' : '1px solid #4B5563',
              backgroundColor: selectedCategory === category.id 
                ? 'linear-gradient(45deg, #EAB545 30%, #F59E0B 90%)'
                : 'background.paper',
              color: selectedCategory === category.id ? 'white' : 'text.primary',
              '&:hover': {
                backgroundColor: selectedCategory === category.id 
                  ? 'linear-gradient(45deg, #F59E0B 30%, #EAB545 90%)'
                  : 'rgba(107, 114, 128, 0.1)',
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