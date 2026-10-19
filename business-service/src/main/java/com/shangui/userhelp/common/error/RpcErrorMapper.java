package com.shangui.userhelp.common.error;

public final class RpcErrorMapper {

    private RpcErrorMapper() {
    }

    public static String mapOrderError(RuntimeException ex) {
        if (ex instanceof BusinessException be) {
            return switch (be.getCode()) {
                case ErrorCode.NOT_FOUND -> "ORDER_NOT_FOUND";
                case ErrorCode.FORBIDDEN -> "ORDER_NOT_OWNED";
                case ErrorCode.BAD_REQUEST -> "INVALID_ARGUMENT";
                default -> "BUSINESS_ERROR";
            };
        }
        return "INTERNAL_ERROR";
    }

    public static String mapRefundError(RuntimeException ex) {
        if (ex instanceof BusinessException be) {
            if ("当前订单状态不允许退款".equals(be.getMessage())) {
                return "REFUND_NOT_ALLOWED";
            }
            if ("idempotency_key 不能为空".equals(be.getMessage())) {
                return "IDEMPOTENCY_KEY_REQUIRED";
            }
            return switch (be.getCode()) {
                case ErrorCode.NOT_FOUND -> "ORDER_NOT_FOUND";
                case ErrorCode.FORBIDDEN -> "ORDER_NOT_OWNED";
                case ErrorCode.BAD_REQUEST -> "INVALID_ARGUMENT";
                default -> "BUSINESS_ERROR";
            };
        }
        return "INTERNAL_ERROR";
    }

    public static String mapTicketError(RuntimeException ex) {
        if (ex instanceof BusinessException be) {
            if (be.getCode() == ErrorCode.BAD_REQUEST) {
                return "INVALID_ARGUMENT";
            }
            return "BUSINESS_ERROR";
        }
        return "INTERNAL_ERROR";
    }

    public static String mapGenericError(RuntimeException ex) {
        if (ex instanceof BusinessException be) {
            return switch (be.getCode()) {
                case ErrorCode.NOT_FOUND -> "NOT_FOUND";
                case ErrorCode.FORBIDDEN -> "FORBIDDEN";
                case ErrorCode.BAD_REQUEST -> "INVALID_ARGUMENT";
                default -> "BUSINESS_ERROR";
            };
        }
        return "INTERNAL_ERROR";
    }
}
