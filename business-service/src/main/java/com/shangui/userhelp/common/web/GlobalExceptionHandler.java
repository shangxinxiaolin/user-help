package com.shangui.userhelp.common.web;

import com.shangui.userhelp.common.error.BusinessException;
import com.shangui.userhelp.common.error.ErrorCode;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiError> handleBusinessException(BusinessException exception) {
        return ResponseEntity.status(httpStatus(exception.getCode()))
                .body(new ApiError(exception.getCode(), exception.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiError> handleException(Exception exception) {
        return ResponseEntity.internalServerError()
                .body(new ApiError(ErrorCode.INTERNAL_ERROR, "系统内部错误"));
    }

    private int httpStatus(int code) {
        return switch (code) {
            case ErrorCode.BAD_REQUEST -> 400;
            case ErrorCode.FORBIDDEN -> 403;
            case ErrorCode.NOT_FOUND -> 404;
            default -> 500;
        };
    }
}
