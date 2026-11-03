"""Real venue changes, season boundaries and compatibility with saved careers."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sim.championship import ChampionshipWorld
from sim.tracks import CALENDAR_2026, calendar_status, get_season_tracks


class CalendarTests(unittest.TestCase):
    def test_confirmed_2026_and_2027_changes(self):
        ids26=[t.id for t in get_season_tracks(2026)]
        ids27=[t.id for t in get_season_tracks(2027)]
        self.assertEqual(len(ids26),23)
        self.assertEqual(ids26[14:17],['azerbaijan','malaysia','singapore'])
        self.assertNotIn('bahrain',ids26)
        self.assertNotIn('saudi',ids26)
        self.assertEqual(len(ids27),24)
        self.assertEqual(ids27[:5],['bahrain','saudi','australia','japan','china'])
        self.assertEqual(set(ids27)-set(ids26),{'bahrain','saudi','portugal','turkey'})
        self.assertEqual(set(ids26)-set(ids27),{'malaysia','barcelona','netherlands'})
        self.assertEqual(sum(t.is_sprint for t in get_season_tracks(2027)),10)

    def test_rotations_and_unpublished_seasons(self):
        for year in range(2028,2031):
            tracks=get_season_tracks(year);ids={t.id for t in tracks}
            self.assertIn('turkey',ids)
            self.assertNotIn('netherlands',ids)
            self.assertEqual('barcelona' in ids,year%2==0)
            self.assertEqual('belgium' in ids,year%2==1)
            self.assertEqual('portugal' in ids,year==2028)
            self.assertEqual([t.round for t in tracks],list(range(1,len(tracks)+1)))
            self.assertEqual(calendar_status(year)['status'],'projection')
        # A track's rounds and Sprints must not leak between cached seasons.
        self.assertEqual(get_season_tracks(2026)[0].id,'australia')
        self.assertFalse(get_season_tracks(2026)[0].is_sprint)
        self.assertTrue(next(t for t in get_season_tracks(2027) if t.id=='australia').is_sprint)

    def test_old_save_preserves_season_then_rolls_into_new_calendar(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'scratch') as tmp:
            path=Path(tmp)/'career.json'
            world=ChampionshipWorld(path)
            world._save_state()
            data=json.loads(path.read_text(encoding='utf-8'))
            data.pop('calendar_version');data.pop('legacy_calendar')
            data['current_round']=14
            path.write_text(json.dumps(data),encoding='utf-8')
            old=ChampionshipWorld(path)
            self.assertEqual(old.current_track.id,'netherlands')
            self.assertEqual([t.id for t in old.calendar],[s['id'] for s in CALENDAR_2026])
            old._save_state()
            resumed=ChampionshipWorld(path)
            self.assertTrue(resumed._legacy_calendar)
            with patch.object(resumed,'_save_state'):
                resumed._start_next_season()
            self.assertEqual(resumed.season_year,2027)
            self.assertEqual(resumed.current_track.id,'bahrain')
            self.assertFalse(resumed._legacy_calendar)
            resumed.current_round=len(resumed.calendar)
            with patch.object(resumed,'_enter_off_season') as end:
                resumed._advance_after_podium()
                end.assert_called_once()

    def test_new_career_uses_selected_season_calendar(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'scratch') as tmp:
            world=ChampionshipWorld(Path(tmp)/'new.json')
            world._init_fresh_career(start_year=2028)
            world._begin_weekend()
            self.assertEqual(world.current_track.id,'bahrain')
            self.assertEqual(world.build_live_tick_payload()['total_rounds'],24)


if __name__=='__main__':unittest.main()
