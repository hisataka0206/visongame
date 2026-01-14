import mediapipe as mp
print("dir(mp):", dir(mp))
try:
    import mediapipe.python.solutions as solutions
    print("Found mediapipe.python.solutions")
except ImportError as e:
    print("ImportError:", e)
    
try:
    print("mp.solutions:", mp.solutions)
except AttributeError:
    print("mp.solutions not found")
