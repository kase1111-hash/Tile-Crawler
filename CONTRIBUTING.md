# Contributing to Tile-Crawler

Thank you for your interest in contributing to Tile-Crawler! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Making Contributions](#making-contributions)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Areas for Contribution](#areas-for-contribution)

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- Git
- OpenAI API Key (for LLM features)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Tile-Crawler.git
   cd Tile-Crawler
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/kase1111-hash/Tile-Crawler.git
   ```

## Development Setup

### Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start development server
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Docker Setup (Alternative)

```bash
# Development mode
docker-compose -f docker-compose.dev.yml up

# Production mode
docker-compose up
```

## Project Structure

```
Tile-Crawler/
├── backend/              # Python FastAPI server
│   ├── main.py          # API entry point
│   ├── game_engine.py   # Core game logic
│   ├── llm_engine.py    # OpenAI integration
│   ├── glyphs/          # GASR glyph system
│   ├── foundry/         # Procedural tile generation
│   ├── auth/            # Authentication system
│   ├── database/        # Persistence layer
│   └── tests/           # Backend tests
├── frontend/            # React TypeScript frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── hooks/       # Custom React hooks
│   │   ├── services/    # API clients
│   │   └── types/       # TypeScript interfaces
│   └── public/          # Static assets
├── data/                # Game content (JSON)
└── docs/                # Documentation
```

## Making Contributions

### Branch Naming

Use descriptive branch names with prefixes:

- `feature/` - New features (e.g., `feature/quest-system`)
- `fix/` - Bug fixes (e.g., `fix/inventory-overflow`)
- `docs/` - Documentation updates (e.g., `docs/api-examples`)
- `refactor/` - Code refactoring (e.g., `refactor/glyph-registry`)
- `test/` - Test additions (e.g., `test/combat-system`)

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(combat): add critical hit mechanics
fix(inventory): prevent duplicate item stacking
docs(api): add WebSocket endpoint documentation
```

### Keeping Your Fork Updated

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

## Coding Standards

### Python (Backend)

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Maximum line length: 127 characters
- Use docstrings for public functions and classes

```python
async def process_action(
    action: str,
    game_state: GameState
) -> ActionResult:
    """
    Process a player action and return the result.

    Args:
        action: The action command (e.g., "north", "take sword")
        game_state: Current game state

    Returns:
        ActionResult containing updated state and narrative
    """
    ...
```

### TypeScript (Frontend)

- Use TypeScript strict mode
- Define interfaces for all data structures
- Use functional components with hooks
- Follow ESLint rules (run `npm run lint`)

```typescript
interface GameMapProps {
  tiles: string[][];
  playerPosition: Position;
  onTileClick?: (position: Position) => void;
}

export const GameMap: React.FC<GameMapProps> = ({
  tiles,
  playerPosition,
  onTileClick
}) => {
  // Component implementation
};
```

### Code Organization

- Keep functions focused and small (< 50 lines preferred)
- Use meaningful variable and function names
- Group related functionality into modules
- Avoid deep nesting (max 3 levels)

## Testing

### Running Backend Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Run specific test file
pytest tests/test_game_flow.py -v

# Run specific test
pytest tests/test_api.py::test_new_game -v
```

### Running Frontend Tests

```bash
cd frontend

# Run E2E tests
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui

# Run in headed mode (see browser)
npm run test:e2e:headed
```

### Writing Tests

- Write tests for all new features
- Maintain or improve test coverage
- Use descriptive test names
- Include both positive and negative test cases

```python
# Backend test example
def test_player_can_pick_up_item():
    """Test that players can successfully pick up items in the room."""
    game = GameEngine()
    game.spawn_item("sword", position=(1, 1))

    result = game.process_action("take sword")

    assert "sword" in game.inventory
    assert result.success is True
```

## Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** with clear, focused commits
3. **Write/update tests** for your changes
4. **Run the test suite** to ensure all tests pass
5. **Update documentation** if needed
6. **Push to your fork** and create a Pull Request

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Tests pass locally (`pytest` and `npm run lint`)
- [ ] New functionality includes tests
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow conventions
- [ ] PR description explains the changes

### Review Process

1. Maintainers will review your PR
2. Address any requested changes
3. Once approved, your PR will be merged
4. Your contribution will be included in the next release

## Areas for Contribution

### Game Designers
- New game mechanics and balance
- Quest system design
- NPC behavior patterns
- Biome content and encounters

### AI Engineers
- LLM prompt optimization
- Memory system improvements
- Response caching strategies
- Context window management

### Artists
- Custom tileset fonts
- UI/UX improvements
- Animation sequences
- Glyph designs

### Frontend Developers
- React component improvements
- Accessibility features
- Mobile responsiveness
- Performance optimization

### Backend Developers
- API endpoint optimization
- Database improvements
- WebSocket enhancements
- Authentication features

### Documentation
- Tutorial content
- API documentation
- Code examples
- Translation/localization

## Questions?

- Open a [GitHub Issue](https://github.com/kase1111-hash/Tile-Crawler/issues) for questions
- Check existing issues and discussions
- Review the [documentation](./docs/README.md)

Thank you for contributing to Tile-Crawler!
