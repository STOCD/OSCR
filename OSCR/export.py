from .datamodels import TreeModel


def analysis_table_export(table_model: TreeModel) -> dict:
    """
    Returns only player combat data from table, only considering one hierachy level below the
    player nodes.

    :param table_model: model containing the table/tree
    """
    data = dict()
    for player in table_model._player._children:
        player_data = [ability.data for ability in player._children]
        data[player.data[0][2]] = player_data
    return data
