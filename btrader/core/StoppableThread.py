__all__ = [
  'StoppableThread'
]

from threading import Thread, Event

class StoppableThread(Thread):
  """Thread class with a stop() method. The thread itself has to check
  regularly for the running() condition."""

  def __init__(self,  *args, **kwargs):
    super(StoppableThread, self).__init__(*args, **kwargs)
    self._stop_event = Event()

  def stop(self):
    self._stop_event.set()

  @property
  def running(self):
    return not self._stop_event.is_set()