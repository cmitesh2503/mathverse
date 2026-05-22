import sys
sys.path.insert(0, 'backend')
from app.api.tutor import _chapter_number_for_session

class S:
    pass

s = S()
s.grade = 10
s.exam = 'cbse'
s.chapter_name = 'Surface Areas and Volumes'
s.current_topic = ''
s.current_chapter_index = 0
print('chapter_no ->', _chapter_number_for_session(s))
