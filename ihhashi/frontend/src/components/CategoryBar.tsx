import { Link } from 'react-router-dom'

interface Category {
  id: string
  name: string
  icon: string
  color?: string
}

interface CategoryBarProps {
  categories: Category[]
  selected?: string
  onSelect?: (id: string) => void
  variant?: 'pills' | 'cards'
  linkPrefix?: string
}

export function CategoryBar({ 
  categories, 
  selected, 
  onSelect, 
  variant = 'pills',
  linkPrefix = '/products'
}: CategoryBarProps) {
  if (variant === 'cards') {
    return (
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
        {categories.map((category) => (
          <Link
            key={category.id}
            to={`${linkPrefix}/${category.id}`}
            className="flex flex-col items-center min-w-[70px] group"
          >
            <div className={`
              w-14 h-14 rounded-2xl flex items-center justify-center text-2xl mb-1.5 
              shadow-sm group-hover:shadow-md transition-all group-hover:scale-105
              ${category.color || 'bg-primary-100'}
            `}>
              {category.icon}
            </div>
            <span className="text-xs text-secondary-500 font-medium group-hover:text-secondary-600">
              {category.name}
            </span>
          </Link>
        ))}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto scrollbar-hide -mx-4 px-4">
      <div className="flex gap-2 py-3 min-w-max">
        {categories.map((category) => {
          const isSelected = selected === category.id
          
          if (onSelect) {
            return (
              <button
                key={category.id}
                onClick={() => onSelect(category.id)}
                className={`
                  flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all
                  ${isSelected
                    ? 'bg-secondary-600 text-primary shadow-md'
                    : 'bg-white text-secondary-500 hover:bg-gray-50 shadow-sm border border-gray-100'
                  }
                `}
              >
                <span>{category.icon}</span>
                <span>{category.name}</span>
              </button>
            )
          }

          return (
            <Link
              key={category.id}
              to={`${linkPrefix}/${category.id}`}
              className={`
                flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all
                ${isSelected
                  ? 'bg-secondary-600 text-primary shadow-md'
                  : 'bg-white text-secondary-500 hover:bg-gray-50 shadow-sm border border-gray-100'
                }
              `}
            >
              <span>{category.icon}</span>
              <span>{category.name}</span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
