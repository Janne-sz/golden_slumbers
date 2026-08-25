import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from severity import apply_breadth, individual_level

T={'trailing_levels':{'1':2,'2':4,'3':6,'5':8},'down_streak_min_days':3,'confluence_required_for_level_3':2,'confluence_required_for_level_5':3,'ma100_escalates_by_levels':1,'breadth':{'daily_drop_threshold_pct':4,'min_count':3,'floor_level_without_gold_confirmation':4,'floor_level_with_gold_confirmation':5,'gold_confirmation_threshold_pct':3}}
def i(**x): return {'available':True,'trailing_drawdown_pct':6,'below_ma50':True,'below_ma100':False,'new_swing_low':True,'down_streak_days':3,'daily_change_pct':-5}|x
def test_ma100_escalator(): assert individual_level(i(below_ma100=True),T)[0]==5
def test_breadth_floor_four_without_gold_confirmation():
 rows=[{'ticker':str(n),'include_in_breadth':True,'severity':1,'indicators':i()} for n in range(3)]
 assert apply_breadth(rows,i(daily_change_pct=-2),T)['floor_level']==4 and all(r['severity']==4 for r in rows)
