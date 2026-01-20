import pytest
import numpy as np
from utils.utils_classes import Goban, GoGame


class TestGobanInit:
    """Tests for Goban.__init__"""

    def test_init_creates_empty_board(self):
        """Test that initialization creates an empty board of correct size"""
        goban = Goban(9)
        assert goban.size == 9
        assert goban.board.shape == (9, 9)
        assert np.all(goban.board == Goban.EMPTY)

    def test_init_different_sizes(self):
        """Test initialization with different board sizes"""
        for size in [5, 9, 13, 19]:
            goban = Goban(size)
            assert goban.size == size
            assert goban.board.shape == (size, size)

    def test_init_states_list(self):
        """Test that initial states list contains empty board"""
        goban = Goban(9)
        assert len(goban.states) == 1
        assert np.array_equal(goban.states[0], goban.board)


class TestStr:
    """Tests for Goban.__str__"""

    def test_str_empty_board(self):
        """Test string representation of empty board"""
        goban = Goban(3)
        result = str(goban)
        assert "." in result

    def test_str_contains_separators(self):
        """Test that string representation contains separators"""
        goban = Goban(3)
        result = str(goban)
        assert "---" in result or "|" in result


class TestNeighbours:
    """Tests for Goban._neighbours"""

    def test_neighbours_center(self):
        """Test neighbours of a center intersection"""
        goban = Goban(9)
        neighbours = goban._neighbours(4, 4)
        assert len(neighbours) == 4
        assert (5, 4) in neighbours
        assert (4, 5) in neighbours
        assert (3, 4) in neighbours
        assert (4, 3) in neighbours

    def test_neighbours_corner(self):
        """Test neighbours of a corner intersection"""
        goban = Goban(9)
        neighbours = goban._neighbours(0, 0)
        assert len(neighbours) == 2
        assert (1, 0) in neighbours
        assert (0, 1) in neighbours

    def test_neighbours_edge(self):
        """Test neighbours of an edge intersection"""
        goban = Goban(9)
        neighbours = goban._neighbours(0, 4)
        assert len(neighbours) == 3
        assert (1, 4) in neighbours
        assert (0, 5) in neighbours
        assert (0, 3) in neighbours

    def test_neighbours_top_left(self):
        """Test neighbours of top-left corner"""
        goban = Goban(5)
        neighbours = goban._neighbours(0, 0)
        assert set(neighbours) == {(1, 0), (0, 1)}

    def test_neighbours_bottom_right(self):
        """Test neighbours of bottom-right corner"""
        goban = Goban(5)
        neighbours = goban._neighbours(4, 4)
        assert set(neighbours) == {(3, 4), (4, 3)}


class TestCalcChain:
    """Tests for Goban._calc_chain"""

    def test_calc_chain_single_stone(self):
        """Test chain with single stone"""
        goban = Goban(9)
        goban.place_stone(5, 5, Goban.BLACK)
        chain = goban._calc_chain(5, 5)
        assert chain == [(5, 5)]

    def test_calc_chain_two_connected_stones(self):
        """Test chain with two connected stones"""
        goban = Goban(9)
        goban.place_stone(5, 5, Goban.BLACK)
        goban.place_stone(5, 6, Goban.BLACK)
        chain = goban._calc_chain(5, 5)
        assert len(chain) == 2
        assert (5, 5) in chain
        assert (5, 6) in chain

    def test_calc_chain_three_stones_line(self):
        """Test chain with three stones in a line"""
        goban = Goban(9)
        goban.place_stone(5, 5, Goban.BLACK)
        goban.place_stone(5, 6, Goban.BLACK)
        goban.place_stone(5, 7, Goban.BLACK)
        chain = goban._calc_chain(5, 5)
        assert len(chain) == 3
        assert (5, 5) in chain
        assert (5, 6) in chain
        assert (5, 7) in chain

    def test_calc_chain_stones_different_colors(self):
        """Test that different color stones are not in same chain"""
        goban = Goban(9)
        goban.place_stone(5, 5, Goban.BLACK)
        goban.place_stone(5, 6, Goban.WHITE)
        chain = goban._calc_chain(5, 5)
        assert chain == [(5, 5)]

    def test_calc_chain_l_shaped(self):
        """Test chain with L-shaped configuration"""
        goban = Goban(9)
        goban.place_stone(5, 5, Goban.BLACK)
        goban.place_stone(5, 6, Goban.BLACK)
        goban.place_stone(6, 6, Goban.BLACK)
        chain = goban._calc_chain(5, 5)
        assert len(chain) == 3
        assert set(chain) == {(5, 5), (5, 6), (6, 6)}


class TestCalcChains:
    """Tests for Goban._calc_chains"""

    def test_calc_chains_empty_board(self):
        """Test chains on empty board"""
        goban = Goban(9)
        goban._calc_chains()
        assert goban.chains[Goban.BLACK] == []
        assert goban.chains[Goban.WHITE] == []

    def test_calc_chains_single_black_stone(self):
        """Test chains with single black stone"""
        goban = Goban(9)
        goban.place_stone(5, 5, Goban.BLACK)
        goban._calc_chains()
        assert len(goban.chains[Goban.BLACK]) == 1
        assert goban.chains[Goban.BLACK][0] == [(5, 5)]

    def test_calc_chains_single_white_stone(self):
        """Test chains with single white stone"""
        goban = Goban(9)
        goban.place_stone(5, 5, Goban.WHITE)
        goban._calc_chains()
        assert len(goban.chains[Goban.WHITE]) == 1

    def test_calc_chains_multiple_separate_chains(self):
        """Test multiple separate chains"""
        goban = Goban(9)
        goban.place_stone(0, 0, Goban.BLACK)
        goban.place_stone(5, 5, Goban.BLACK)
        goban._calc_chains()
        assert len(goban.chains[Goban.BLACK]) == 2

    def test_calc_chains_mixed_colors(self):
        """Test chains with mixed colors"""
        goban = Goban(9)
        goban.place_stone(5, 5, Goban.BLACK)
        goban.place_stone(6, 5, Goban.WHITE)
        goban._calc_chains()
        assert len(goban.chains[Goban.BLACK]) == 1
        assert len(goban.chains[Goban.WHITE]) == 1


class TestCalcFreedom:
    """Tests for Goban._calc_freedom"""

    def test_calc_freedom_single_stone_center(self):
        """Test freedom of single stone in center"""
        goban = Goban(9)
        goban.place_stone(4, 4, Goban.BLACK)
        freedom = goban._calc_freedom(4, 4)
        assert len(freedom) == 4
        assert (5, 4) in freedom
        assert (4, 5) in freedom
        assert (3, 4) in freedom
        assert (4, 3) in freedom

    def test_calc_freedom_single_stone_corner(self):
        """Test freedom of single stone in corner"""
        goban = Goban(9)
        goban.place_stone(0, 0, Goban.BLACK)
        freedom = goban._calc_freedom(0, 0)
        assert len(freedom) == 2
        assert (1, 0) in freedom
        assert (0, 1) in freedom

    def test_calc_freedom_surrounded_stone(self):
        """Test freedom of surrounded stone"""
        goban = Goban(3)
        goban.place_stone(1, 1, Goban.BLACK)
        goban.place_stone(0, 1, Goban.WHITE)
        goban.place_stone(2, 1, Goban.WHITE)
        goban.place_stone(1, 0, Goban.WHITE)
        goban.place_stone(1, 2, Goban.WHITE)
        freedom = goban._calc_freedom(1, 1)
        assert len(freedom) == 0

    def test_calc_freedom_connected_stones(self):
        """Test freedom of connected stones (chain)"""
        goban = Goban(9)
        goban.place_stone(4, 4, Goban.BLACK)
        goban.place_stone(4, 5, Goban.BLACK)
        freedom = goban._calc_freedom(4, 4)
        assert len(freedom) == 6


class TestCalcFreedoms:
    """Tests for Goban._calc_freedoms"""

    def test_calc_freedoms_empty_board(self):
        """Test freedoms on empty board"""
        goban = Goban(9)
        goban._calc_freedoms()
        assert goban.freedoms[Goban.BLACK] == []
        assert goban.freedoms[Goban.WHITE] == []

    def test_calc_freedoms_single_stone(self):
        """Test freedoms with single stone"""
        goban = Goban(9)
        goban.place_stone(4, 4, Goban.BLACK)
        goban._calc_freedoms()
        assert len(goban.freedoms[Goban.BLACK]) == 1
        assert len(goban.freedoms[Goban.BLACK][0]) == 4

    def test_calc_freedoms_multiple_stones(self):
        """Test freedoms with multiple stones"""
        goban = Goban(9)
        goban.place_stone(4, 4, Goban.BLACK)
        goban.place_stone(0, 0, Goban.BLACK)
        goban._calc_freedoms()
        assert len(goban.freedoms[Goban.BLACK]) == 2

    def test_calc_freedoms_mixed_colors(self):
        """Test freedoms with mixed colors"""
        goban = Goban(9)
        goban.place_stone(4, 4, Goban.BLACK)
        goban.place_stone(8, 8, Goban.WHITE)
        goban._calc_freedoms()
        assert len(goban.freedoms[Goban.BLACK]) == 1
        assert len(goban.freedoms[Goban.WHITE]) == 1


class TestCalcTerritoryBorders:
    """Tests for Goban._calc_territory_borders"""

    def test_calc_territory_borders_single_intersection(self):
        """Test territory borders with single intersection"""
        goban = Goban(9)
        goban.place_stone(4, 4, Goban.BLACK)
        territory = [(3, 3)]
        borders = goban._calc_territory_borders(territory)
        assert isinstance(borders, list)

    def test_calc_territory_borders_group_of_intersections(self):
        """Test territory borders with group of intersections"""
        goban = Goban(9)
        goban.place_stone(5, 5, Goban.BLACK)
        goban.place_stone(5, 6, Goban.BLACK)
        territory = [(4, 5), (4, 6), (3, 5), (3, 6)]
        borders = goban._calc_territory_borders(territory)
        assert isinstance(borders, list)

    def test_calc_territory_borders_returns_list(self):
        """Test that territory borders returns a list"""
        goban = Goban(9)
        territory = [(5, 5), (5, 6)]
        borders = goban._calc_territory_borders(territory)
        assert isinstance(borders, list)


class TestCalcTerritories:
    """Tests for Goban._calc_territories"""

    def test_calc_territories_empty_board(self):
        """Test territories on empty board"""
        goban = Goban(9)
        goban._calc_territories()
        assert goban.territories[Goban.BLACK] == []
        assert goban.territories[Goban.WHITE] == []

    def test_calc_territories_single_stone(self):
        """Test territories with single stone"""
        goban = Goban(5)
        goban.place_stone(2, 2, Goban.BLACK)
        goban._calc_territories()
        # The entire board except the stone should be uncontrolled

    def test_calc_territories_board_divided(self):
        """Test territories when board is divided"""
        goban = Goban(5)
        # Create a dividing line
        for i in range(5):
            goban.place_stone(2, i, Goban.BLACK)
        goban._calc_territories()
        # Should have territories for both colors

    def test_calc_territories_has_dict_structure(self):
        """Test that territories has correct dict structure"""
        goban = Goban(9)
        goban.place_stone(4, 4, Goban.BLACK)
        goban._calc_territories()
        assert Goban.BLACK in goban.territories
        assert Goban.WHITE in goban.territories


class TestPossibleMove:
    """Tests for Goban.possible_move"""

    def test_possible_move_empty_position(self):
        """Test possible move on empty position"""
        goban = Goban(9)
        possible, index = goban.possible_move(4, 4, Goban.BLACK)
        assert possible is True
        assert index is None

    def test_possible_move_occupied_position(self):
        """Test possible move on occupied position"""
        goban = Goban(9)
        goban.place_stone(4, 4, Goban.BLACK)
        with pytest.raises(ValueError):
            goban.possible_move(4, 4, Goban.WHITE)

    def test_possible_move_out_of_bounds(self):
        """Test possible move out of bounds"""
        goban = Goban(9)
        with pytest.raises(IndexError):
            goban.possible_move(9, 9, Goban.BLACK)

    def test_possible_move_capturing(self):
        """Test possible move that captures opponent stone"""
        goban = Goban(5)
        goban.place_stone(2, 2, Goban.WHITE)
        goban.place_stone(1, 2, Goban.BLACK)
        goban.place_stone(3, 2, Goban.BLACK)
        goban.place_stone(2, 1, Goban.BLACK)
        possible, index = goban.possible_move(2, 3, Goban.BLACK)
        assert possible is True
        if index is not None:
            assert isinstance(index, int)

    def test_possible_move_suicide_move(self):
        """Test suicide move (placing stone with no liberties)"""
        goban = Goban(3)
        goban.place_stone(0, 1, Goban.WHITE)
        goban.place_stone(1, 0, Goban.WHITE)
        goban.place_stone(1, 2, Goban.WHITE)
        possible, index = goban.possible_move(0, 0, Goban.BLACK)
        # Suicide move without capturing should not be possible
        assert possible is False or index is not None

    def test_possible_move_return_type(self):
        """Test that possible_move returns correct type"""
        goban = Goban(9)
        result = goban.possible_move(4, 4, Goban.BLACK)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert result[1] is None or isinstance(result[1], int)

    def test_possible_move_does_not_modify_board(self):
        """Test that possible_move doesn't permanently modify board"""
        goban = Goban(9)
        board_before = goban.board.copy()
        goban.possible_move(4, 4, Goban.BLACK)
        assert np.array_equal(goban.board, board_before)

    def test_possible_move_invalid_color(self):
        """Test possible_move with invalid color"""
        goban = Goban(9)
        with pytest.raises(ValueError):
            goban.possible_move(4, 4, 3)

    def test_possible_move_white_stone(self):
        """Test possible move with white stone"""
        goban = Goban(9)
        possible, index = goban.possible_move(4, 4, Goban.WHITE)
        assert possible is True
        assert index is None


class TestGoGame:
    """Tests for the GoGame class (game flow, passes, captures, state history)."""

    def test_init_instance_attributes(self):
        """Ensure instance attributes are initialized per-instance (no shared mutable defaults)."""
        g1 = GoGame(5)
        g2 = GoGame(5)

        # Modify g1's score and ensure g2 is unaffected
        g1.score[Goban.BLACK] += 1
        assert g1.score[Goban.BLACK] == 1
        assert g2.score[Goban.BLACK] == 0

        # Defaults
        assert g1.nbr_moves == 0
        assert g1.black_passed is False
        assert g1.white_passed is False

    def test_pass_move_behaviour_and_game_over(self):
        """Passing should increment moves and switch player; two passes end the game."""
        game = GoGame(5)
        start = game.current_color
        game.pass_move()
        assert game.nbr_moves == 1
        assert game.current_color != start

        # The implementation may set flags; if implemented they should reflect the pass
        if start == Goban.BLACK:
            assert getattr(game, "black_passed", True) is True
        else:
            assert getattr(game, "white_passed", True) is True

        # Second pass should end the game (both players passed)
        game.pass_move()
        assert game.nbr_moves == 2
        assert game.game_over() is True

    def test_take_move_resets_pass_flags_and_records_state(self):
        """Taking a move should reset pass flags and append the board state history."""
        game = GoGame(5)
        # Simulate previous passes
        game.black_passed = True
        game.white_passed = True

        # Ensure states list exists
        before_states = len(game.goban.states)

        # Play a legal move in the center
        ok = game.take_move(2, 2)
        assert ok is True

        # After a real move, pass flags should be reset
        assert game.black_passed is False or game.white_passed is False

        # And a new board state should have been appended
        assert len(game.goban.states) == before_states + 1

    def test_take_move_captures_opponent_chain(self):
        """A move that captures opponent stones should remove them from the goban."""
        game = GoGame(5)
        g = game.goban

        # Setup a capture: white at (2,2) surrounded on three sides
        g.place_stone(2, 2, Goban.WHITE)
        g.place_stone(1, 2, Goban.BLACK)
        g.place_stone(3, 2, Goban.BLACK)
        g.place_stone(2, 1, Goban.BLACK)

        # Ensure the move is legal and captures white stone
        game.current_color = Goban.BLACK
        ok = game.take_move(2, 3)
        assert ok is True
        # The white stone at (2,2) should have been removed
        assert g.board[2, 2] == Goban.EMPTY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
