#imports
import numpy as np
import cv2
import matplotlib.image as mpimg
import matplotlib.pyplot as plt

#useful methods
def undistort_image(img, cameraMatrix, distCoeffs):
    undist = cv2.undistort(img, cameraMatrix, distCoeffs, None, cameraMatrix)
    return undist

def hls_threshold(img, h_thresh=(0, 255), s_thresh=(0, 255), display=False):
    hls = cv2.cvtColor(img, cv2.COLOR_BGR2HLS)
    # H channel
    h_channel = hls[:,:,0]
    h_threshold = np.zeros_like(h_channel)
    h_threshold[(h_channel > h_thresh[0]) & (h_channel <= h_thresh[1])] = 1
    if display:
        out_img = np.dstack((h_threshold, h_threshold, h_threshold))*255
        cv2.imshow('h_threshold', out_img) 
        cv2.waitKey(10)
        cv2.imwrite('./output_images/03-h_threshold.jpg',out_img)
    # S channel
    s_channel = hls[:,:,2]
    s_threshold = np.zeros_like(s_channel)
    s_threshold[(s_channel > s_thresh[0]) & (s_channel <= s_thresh[1])] = 1
    if display:
        out_img = np.dstack((s_threshold, s_threshold, s_threshold))*255
        cv2.imshow('s_threshold', out_img) 
        cv2.waitKey(10)
        cv2.imwrite('./output_images/04-s_threshold.jpg',out_img)
    hls_threshold = np.zeros_like(h_threshold)
    hls_threshold[(h_threshold == 1) & (s_threshold == 1)] = 1
    if display:
        out_img = np.dstack((hls_threshold, hls_threshold, hls_threshold))*255
        cv2.imshow('hls_threshold', out_img)
        cv2.waitKey(10)
        cv2.imwrite('./output_images/05-hls_threshold.jpg',out_img)
    return hls_threshold

def red_threshold(img, thresh=(0,255), display=False):
    red_channel = img[:,:,2]
    red_threshold = np.zeros_like(red_channel)
    red_threshold[(red_channel > thresh[0]) & (red_channel <= thresh[1])] = 1
    if display:
        out_img = np.dstack((red_threshold, red_threshold, red_threshold))*255
        cv2.imshow('red_threshold', out_img)
        cv2.waitKey(10)
        cv2.imwrite('./output_images/06-r_threshold.jpg',out_img)
    return red_threshold

def abs_sobel_threshold(img, orient='x', thresh=(0,255), display=False):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if orient == 'x':
        abs_sobel = np.absolute(cv2.Sobel(gray, cv2.CV_64F, 1, 0))
    if orient == 'y':
        abs_sobel = np.absolute(cv2.Sobel(gray, cv2.CV_64F, 0, 1))
    # Rescale back to 8 bit integer
    scaled_sobel = np.uint8(255*abs_sobel/np.max(abs_sobel))
    # Create a copy and apply the threshold
    binary_output_sobel = np.zeros_like(scaled_sobel)
    # Here I'm using inclusive (>=, <=) thresholds, but exclusive is ok too
    binary_output_sobel[(scaled_sobel >= thresh[0]) & (scaled_sobel <= thresh[1])] = 1
    if display:
        out_img = np.dstack((binary_output_sobel, binary_output_sobel, binary_output_sobel))*255
        cv2.imshow('sobel_threshold', out_img)
        cv2.waitKey(10)
        if orient == 'x':
            cv2.imwrite('./output_images/06.1-sobel_x_threshold.jpg',out_img)
        elif orient == 'y':
            cv2.imwrite('./output_images/06.1-sobel_y_threshold.jpg',out_img)
    # Return the result
    return binary_output_sobel

def convert_to_binary(img, display=False):
    img = cv2.GaussianBlur(img, (3, 3), 0)
    red_binary = red_threshold(img, thresh=(150,255), display=display)
    hls_binary = hls_threshold(img, h_thresh=(15,100), s_thresh=(90,255), display=display)
    x_binary = abs_sobel_threshold(img,thresh=(25, 200), display=display)
    y_binary = abs_sobel_threshold(img,thresh=(25, 200), orient='y', display=display)
    binary_output_color = np.zeros_like(red_binary)
    binary_output_color[(red_binary == 1) & (hls_binary == 1)] = 1
    binary_output_sobel = np.zeros_like(red_binary)
    binary_output_sobel[(x_binary == 1) & (y_binary == 1)] = 1
    binary_output = cv2.bitwise_or(binary_output_color, binary_output_sobel)
    return binary_output

def region_of_interest(img, vertices):
    #defining a blank mask to start with
    mask = np.zeros_like(img)

    #defining a 3 channel or 1 channel color to fill the mask with depending on the input image
    if len(img.shape) > 2:
        channel_count = img.shape[2]  # i.e. 3 or 4 depending on your image
        ignore_mask_color = (255,) * channel_count
    else:
        ignore_mask_color = 255

    #filling pixels inside the polygon defined by "vertices" with the fill color
    cv2.fillPoly(mask, vertices, ignore_mask_color)

    #returning the image only where mask pixels are nonzero
    masked_image = cv2.bitwise_and(img, mask)
    return masked_image

def getPerspectiveTransform(source_points, destination_points):
    M = cv2.getPerspectiveTransform(source_points, destination_points)
    return M

def top_down_view(img, M):
    img_size = (img.shape[1],img.shape[0])
    warped = cv2.warpPerspective(img, M, img_size, flags=cv2.INTER_LINEAR)
    return warped

def hist(img):
    bottom_half = img[img.shape[0]//2:,:]
    histogram = np.sum(bottom_half, axis=0)
    return histogram

def find_lines_sliding_window(binary_warped, window_search, display):
    
    histogram = np.sum(binary_warped[int(binary_warped.shape[0]/2):,:], axis=0)
    
    out_img = np.dstack((binary_warped, binary_warped, binary_warped))*255

    # we need max for each half of the histogram. the example above shows how
    # things could be complicated if didn't split the image in half 
    # before taking the top 2 maxes
    midpoint = np.int(histogram.shape[0]/2)
    leftx_base = np.argmax(histogram[:midpoint])
    rightx_base = np.argmax(histogram[midpoint:]) + midpoint
    
    # Choose the number of sliding windows
    # this will throw an error in the height if it doesn't evenly divide the img height
    nwindows = 9
    # Set height of windows
    window_height = np.int(binary_warped.shape[0]/nwindows)
    
    # Identify the x and y positions of all nonzero pixels in the image
    nonzero = binary_warped.nonzero()
    nonzeroy = np.array(nonzero[0])
    nonzerox = np.array(nonzero[1])
    
    # Current positions to be updated for each window
    leftx_current = leftx_base
    rightx_current = rightx_base
    
    # Set the width of the windows +/- margin
    margin = 100
    # Set minimum number of pixels found to recenter window
    minpix = 50
    # Create empty lists to receive left and right lane pixel indices
    left_lane_inds = []
    right_lane_inds = []

    # Step through the windows one by one
    for window in range(nwindows):
        # Identify window boundaries in x and y (and right and left)
        win_y_low = int(binary_warped.shape[0] - (window+1)*window_height)
        win_y_high = int(binary_warped.shape[0] - window*window_height)
        win_xleft_low = leftx_current - margin
        win_xleft_high = leftx_current + margin
        win_xright_low = rightx_current - margin
        win_xright_high = rightx_current + margin

        # Draw the windows on the visualization image
        cv2.rectangle(out_img,(win_xleft_low,win_y_low),(win_xleft_high,win_y_high),(0,255,0), 3) 
        cv2.rectangle(out_img,(win_xright_low,win_y_low),(win_xright_high,win_y_high),(0,255,0), 3) 

        # Identify the nonzero pixels in x and y within the window
        good_left_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) & (nonzerox >= win_xleft_low) & (nonzerox < win_xleft_high)).nonzero()[0]
        good_right_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) & (nonzerox >= win_xright_low) & (nonzerox < win_xright_high)).nonzero()[0]
        # Append these indices to the lists
        left_lane_inds.append(good_left_inds)
        right_lane_inds.append(good_right_inds)
        # If you found > minpix pixels, recenter next window on their mean position
        if len(good_left_inds) > minpix:
            leftx_current = np.int(np.mean(nonzerox[good_left_inds]))
        if len(good_right_inds) > minpix:        
            rightx_current = np.int(np.mean(nonzerox[good_right_inds]))

            
    # Concatenate the arrays of indices
    left_lane_inds = np.concatenate(left_lane_inds)
    right_lane_inds = np.concatenate(right_lane_inds)

    # Extract left and right line pixel positions
    leftx = nonzerox[left_lane_inds]
    lefty = nonzeroy[left_lane_inds] 
    rightx = nonzerox[right_lane_inds]
    righty = nonzeroy[right_lane_inds]

    # Fit a second order polynomial to each
    left_fit = np.polyfit(lefty, leftx, 2)
    right_fit = np.polyfit(righty, rightx, 2)
    
    # Generate x and y values for plotting
    ploty = np.linspace(0, binary_warped.shape[0]-1, binary_warped.shape[0] )
    left_fitx = left_fit[0]*ploty**2 + left_fit[1]*ploty + left_fit[2]
    right_fitx = right_fit[0]*ploty**2 + right_fit[1]*ploty + right_fit[2]

    nonzero = binary_warped.nonzero()
    nonzeroy = np.array(nonzero[0])
    nonzerox = np.array(nonzero[1])
    margin = 100
    left_lane_inds = ((nonzerox > (left_fit[0]*(nonzeroy**2) + left_fit[1]*nonzeroy + left_fit[2] - margin)) & (nonzerox < (left_fit[0]*(nonzeroy**2) + left_fit[1]*nonzeroy + left_fit[2] + margin))) 
    right_lane_inds = ((nonzerox > (right_fit[0]*(nonzeroy**2) + right_fit[1]*nonzeroy + right_fit[2] - margin)) & (nonzerox < (right_fit[0]*(nonzeroy**2) + right_fit[1]*nonzeroy + right_fit[2] + margin)))  

    # Again, extract left and right line pixel positions
    leftx = nonzerox[left_lane_inds]
    lefty = nonzeroy[left_lane_inds] 
    rightx = nonzerox[right_lane_inds]
    righty = nonzeroy[right_lane_inds]
    # Fit a second order polynomial to each
    left_fit = np.polyfit(lefty, leftx, 2)
    right_fit = np.polyfit(righty, rightx, 2)

    if display:
        out_img[lefty, leftx] = [255, 0, 0]
        out_img[righty, rightx] = [0, 0, 255]
        # Plots the left and right polynomials on the lane lines
        plt.plot(left_fitx, ploty, color='yellow')
        plt.plot(right_fitx, ploty, color='yellow')
        plt.imshow(out_img)
        mpimg.imsave('./output_images/10-window_search.jpg',out_img)

    return left_fit, right_fit, leftx, lefty, rightx, righty, window_search

def find_lines_from_prior(binary_warped, left_fit, right_fit, window_search, frame_count, display):
    
    # repeat window search to maintain stability
    if frame_count % 10 == 0:
        window_search=True
        
    nonzero = binary_warped.nonzero()
    nonzeroy = np.array(nonzero[0])
    nonzerox = np.array(nonzero[1])
    margin = 100
    left_lane_inds = ((nonzerox > (left_fit[0]*(nonzeroy**2) + left_fit[1]*nonzeroy + left_fit[2] - margin)) & (nonzerox < (left_fit[0]*(nonzeroy**2) + left_fit[1]*nonzeroy + left_fit[2] + margin))) 
    right_lane_inds = ((nonzerox > (right_fit[0]*(nonzeroy**2) + right_fit[1]*nonzeroy + right_fit[2] - margin)) & (nonzerox < (right_fit[0]*(nonzeroy**2) + right_fit[1]*nonzeroy + right_fit[2] + margin)))  

    # Again, extract left and right line pixel positions
    leftx = nonzerox[left_lane_inds]
    lefty = nonzeroy[left_lane_inds] 
    rightx = nonzerox[right_lane_inds]
    righty = nonzeroy[right_lane_inds]
    # Fit a second order polynomial to each
    left_fit = np.polyfit(lefty, leftx, 2)
    right_fit = np.polyfit(righty, rightx, 2)
    # Generate x and y values for plotting
    ploty = np.linspace(0, binary_warped.shape[0]-1, binary_warped.shape[0] )
    left_fitx = left_fit[0]*ploty**2 + left_fit[1]*ploty + left_fit[2]
    right_fitx = right_fit[0]*ploty**2 + right_fit[1]*ploty + right_fit[2]

    if display:
        out_img = np.dstack((binary_warped, binary_warped, binary_warped))*255
        out_img[lefty, leftx] = [255, 0, 0]
        out_img[righty, rightx] = [0, 0, 255]
        # Plots the left and right polynomials on the lane lines
        plt.plot(left_fitx, ploty, color='yellow')
        plt.plot(right_fitx, ploty, color='yellow')
        plt.imshow(out_img)
        mpimg.imsave('./output_images/11-lines_from_prior.jpg',out_img)


    return left_fit, right_fit, leftx, lefty, rightx, righty, window_search

def get_val(y, poly_coeff):
    return poly_coeff[0]*y**2 + poly_coeff[1]*y + poly_coeff[2]

def lane_fill_poly(binary_warped, undist, left_fit, right_fit, M_inv):
    
    # Generate x and y values
    ploty = np.linspace(0, binary_warped.shape[0]-1, binary_warped.shape[0])

    left_fitx = get_val(ploty,left_fit)
    right_fitx = get_val(ploty,right_fit)
    
    # Create an image to draw the lines on
    warp_zero = np.zeros_like(binary_warped).astype(np.uint8)
    color_warp = np.dstack((warp_zero, warp_zero, warp_zero))

    # Recast x and y for cv2.fillPoly()
    pts_left = np.array([np.transpose(np.vstack([left_fitx, ploty]))])
    pts_right = np.array([np.flipud(np.transpose(np.vstack([right_fitx, ploty])))])
    pts = np.hstack((pts_left, pts_right))

    # Draw the lane 
    cv2.fillPoly(color_warp, np.int_([pts]), (0,255, 0))

    # Warp using inverse perspective transform
    newwarp = cv2.warpPerspective(color_warp, M_inv, (binary_warped.shape[1], binary_warped.shape[0])) 
    # overlay
    result = cv2.addWeighted(undist, 1, newwarp, 0.3, 0)

    return result

def measure_curve(binary_warped, left_fit, right_fit):
    # generate y values 
    ploty = np.linspace(0, binary_warped.shape[0]-1, binary_warped.shape[0] )
    
    # measure radius at the maximum y value, or bottom of the image
    # this is closest to the car 
    y_eval = np.max(ploty)
    
    # coversion rates for pixels to metric
    ym_per_pix = 30/720 # meters per pixel in y dimension
    xm_per_pix = 3.7/700 # meters per pixel in x dimension
   
    # x positions lanes
    leftx = get_val(ploty,left_fit)
    rightx = get_val(ploty,right_fit)

    # fit polynomials in metric 
    left_fit_cr = np.polyfit(ploty*ym_per_pix, leftx*xm_per_pix, 2)
    right_fit_cr = np.polyfit(ploty*ym_per_pix, rightx*xm_per_pix, 2)
    
    # calculate radii in metric from radius of curvature formula
    left_curverad = ((1 + (2*left_fit_cr[0]*y_eval*ym_per_pix + left_fit_cr[1])**2)**1.5) / np.absolute(2*left_fit_cr[0])
    right_curverad = ((1 + (2*right_fit_cr[0]*y_eval*ym_per_pix + right_fit_cr[1])**2)**1.5) / np.absolute(2*right_fit_cr[0])
    
    # averaged radius of curvature of left and right in real world space
    # should represent approximately the center of the road
    curve_rad = round((left_curverad + right_curverad)/2)
    
    return curve_rad

def vehicle_offset(img, left_fit, right_fit):  
    xm_per_pix = 3.7/700 
    image_center = img.shape[1]/2
    
    ## find where lines hit the bottom of the image, closest to the car
    left_low = get_val(img.shape[0],left_fit)
    right_low = get_val(img.shape[0],right_fit)
    
    # pixel coordinate for center of lane
    lane_center = (left_low+right_low)/2.0
    
    ## vehicle offset
    distance = image_center - lane_center
    
    ## convert to metric
    return (round(distance*xm_per_pix,5))

def sanity_check(left_fit, leftx, right_fit, rightx, distance_threshold=(2.5, 5.0)):
    xm_per_pix = 3.7/700 
    current_lines_distance = (np.average(rightx) - np.average(leftx))*xm_per_pix
    print("current_lines_distance = {}".format(current_lines_distance))
    cond = current_lines_distance >= distance_threshold[0]\
                and\
                current_lines_distance <= distance_threshold[1]
    return cond