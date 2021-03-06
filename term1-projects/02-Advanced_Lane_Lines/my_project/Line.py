import numpy as np

# Define a class to receive the characteristics of each line detection
class Line():
    def __init__(self):
        # was the line detected in the last iteration?
        self.detected = False
        # x values of the last n fits of the line
        self.recent_xfitted = []
        #average x values of the fitted line over the last n iterations
        self.bestx = None
        #polynomial coefficients averaged over the last n iterations
        self.best_fit = []
        #polynomial coefficients for the most recent fit
        self.current_fit = np.array([0,0,0], dtype='float')
        #radius of curvature of the line in some units
        self.radius_of_curvature = None
        #distance in meters of vehicle center from the line
        self.line_base_pos = None
        #difference in fit coefficients between last and new fits
        self.diffs = np.array([0,0,0], dtype='float')
        #x values for detected line pixels
        self.allx = None
        #y values for detected line pixels
        self.ally = None
        #temporal window size
        self.n = 10

    def updateLine(self, fit, fitx, fity):
        self.current_fit = fit
        self.allx = fitx
        self.ally = fity

        self.updateBests()

    def updateBests(self):
        if self.best_fit == []:
            self.best_fit = self.current_fit
        else:
            self.best_fit = incrementalAverage(self.best_fit, self.current_fit, self.n)

        if len(self.recent_xfitted) > self.n:
            self.recent_xfitted.pop(0)
        self.recent_xfitted.append(np.average(self.allx))
        
        self.bestx = np.average(self.recent_xfitted)
        


def incrementalAverage(avg, x, n):
    return (avg + ((x-avg)/n))

